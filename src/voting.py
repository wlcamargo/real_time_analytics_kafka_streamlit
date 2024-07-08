import random
import time
from datetime import datetime

import psycopg2
import simplejson as json
from confluent_kafka import Consumer, KafkaException, KafkaError, SerializingProducer

from producer import delivery_report

conf = {
    'bootstrap.servers': 'localhost:9092',
}

consumer = Consumer(conf | {
    'group.id': 'voting-group',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False
})

producer = SerializingProducer(conf)

if __name__ == "__main__":
    conn = psycopg2.connect("host=localhost dbname=voting user=postgres password=postgres")
    cur = conn.cursor()

    # Carregar candidatos do banco de dados
    cur.execute("""
        SELECT candidate_id, candidate_name, position, photo_url
        FROM candidates
    """)
    candidates = cur.fetchall()
    candidates = [{"candidate_id": c[0], "candidate_name": c[1], "position": c[2], "photo_url": c[3]} for c in candidates]
    if not candidates:
        raise Exception("No candidates found in database")
    else:
        print(candidates)

    consumer.subscribe(['voters_topic'])
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            elif msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(msg.error())
                    break
            else:
                voter = json.loads(msg.value().decode('utf-8'))
                chosen_candidate = random.choice(candidates)
                vote = voter | chosen_candidate | {
                    "voting_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "vote": 1
                }

                try:
                    print("User {} is voting for candidate: {}".format(vote['voter_id'], vote['candidate_id']))
                    cur.execute("""
                            INSERT INTO votes (voter_id, candidate_id, voting_time)
                            VALUES (%s, %s, %s)
                        """, (vote['voter_id'], vote['candidate_id'], vote['voting_time']))

                    conn.commit()

                    producer.produce(
                        'votes_topic',
                        key=vote["voter_id"],
                        value=json.dumps(vote),
                        on_delivery=delivery_report
                    )
                    producer.poll(0)
                except Exception as e:
                    print("Error: {}".format(e))
                    continue
            time.sleep(0.2)
    except KafkaException as e:
        print(e)
