import json
import os
import time
from pathlib import Path

from confluent_kafka import SerializingProducer
from confluent_kafka.serialization import StringSerializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer


def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed for key={msg.key()}: {err}")
    else:
        print(f"Delivered to {msg.topic()}[{msg.partition()}]@{msg.offset()} key={msg.key()}")


def load_avro_schema(schema_path: str) -> str:
    with open(schema_path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    bootstrap = ",".join([
        "rc1b-6v254d3mu3mlhcg5.mdb.yandexcloud.net:9091",
        "rc1b-ga7q4l5c43kes7ms.mdb.yandexcloud.net:9091",
        "rc1b-tl2r3tk8eaau7h4d.mdb.yandexcloud.net:9091",
    ])

    topic = os.environ.get("KAFKA_TOPIC", "app.events")
    sr_url = os.environ.get("SCHEMA_REGISTRY_URL", "http://localhost:8081")
    schema_path = os.environ.get("AVRO_SCHEMA", str(Path(__file__).resolve().parent.parent / "schema" / "app_event.avsc"))

    value_schema_str = load_avro_schema(schema_path)

    sr_conf = {"url": sr_url}
    sr_client = SchemaRegistryClient(sr_conf)
    value_serializer = AvroSerializer(schema_registry_client=sr_client, schema_str=value_schema_str)

    producer_conf = {
        "bootstrap.servers": bootstrap,
        "security.protocol": "SASL_SSL",
        "ssl.ca.location": str(Path("/home/bpp/kafka-demo/certs/CA.pem")),
        "sasl.mechanism": "SCRAM-SHA-512",
        "sasl.username": os.environ.get("KAFKA_USERNAME", "user123"),
        "sasl.password": os.environ.get("KAFKA_PASSWORD", "password123"),
        "key.serializer": StringSerializer("utf_8"),
        "value.serializer": value_serializer,
        "linger.ms": 50,
        "acks": "all",
    }

    producer = SerializingProducer(producer_conf)

    now_ms = int(time.time() * 1000)
    messages = [
        {
            "id": f"evt-{i}",
            "event_type": "test",
            "payload": json.dumps({"i": i}),
            "timestamp_ms": now_ms + i,
        }
        for i in range(5)
    ]

    for i, payload in enumerate(messages):
        key = payload["id"]
        try:
            producer.produce(topic=topic, key=key, value=payload, on_delivery=delivery_report)
        except BufferError:
            producer.poll(0)
            producer.produce(topic=topic, key=key, value=payload, on_delivery=delivery_report)
        producer.poll(0)

    producer.flush(10)


if __name__ == "__main__":
    main()

