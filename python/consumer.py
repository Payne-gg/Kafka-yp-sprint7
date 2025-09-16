import os
from pathlib import Path
from typing import Optional

from confluent_kafka import DeserializingConsumer
from confluent_kafka.serialization import StringDeserializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer


def main():
    bootstrap = ",".join([
        "rc1b-6v254d3mu3mlhcg5.mdb.yandexcloud.net:9091",
        "rc1b-ga7q4l5c43kes7ms.mdb.yandexcloud.net:9091",
        "rc1b-tl2r3tk8eaau7h4d.mdb.yandexcloud.net:9091",
    ])

    topic = os.environ.get("KAFKA_TOPIC", "app.events")
    sr_url = os.environ.get("SCHEMA_REGISTRY_URL", "http://localhost:8081")

    sr_conf = {"url": sr_url}
    sr_client = SchemaRegistryClient(sr_conf)
    value_deserializer = AvroDeserializer(schema_registry_client=sr_client)

    consumer_conf = {
        "bootstrap.servers": bootstrap,
        "security.protocol": "SASL_SSL",
        "ssl.ca.location": str(Path("/home/bpp/kafka-demo/certs/CA.pem")),
        "sasl.mechanism": "SCRAM-SHA-512",
        "sasl.username": os.environ.get("KAFKA_USERNAME", "user123"),
        "sasl.password": os.environ.get("KAFKA_PASSWORD", "password123"),
        "key.deserializer": StringDeserializer("utf_8"),
        "value.deserializer": value_deserializer,
        "group.id": os.environ.get("KAFKA_GROUP_ID", "app.events.demo.group"),
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
        "session.timeout.ms": 45000,
    }

    consumer = DeserializingConsumer(consumer_conf)
    consumer.subscribe([topic])

    max_messages = int(os.environ.get("MAX_MESSAGES", "5"))
    received = 0
    try:
        while received < max_messages:
            msg = consumer.poll(5.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Error: {msg.error()}")
                continue
            print(
                f"Received from {msg.topic()}[{msg.partition()}]@{msg.offset()} key={msg.key()} value={msg.value()}"
            )
            received += 1
    finally:
        consumer.close()


if __name__ == "__main__":
    main()

