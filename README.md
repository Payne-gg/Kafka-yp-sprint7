## Практика: Schema Registry и продюсер/консьюмер в Yandex Cloud

### Вводные
- **Kafka брокеры**: rc1b-6v254d3mu3mlhcg5.mdb.yandexcloud.net:9091, rc1b-ga7q4l5c43kes7ms.mdb.yandexcloud.net:9091, rc1b-tl2r3tk8eaau7h4d.mdb.yandexcloud.net:9091
- **SASL SCRAM**: user123 / password123
- **Топики**: `app.events`, `schemas` (для Schema Registry)
- **SR URL**: http://localhost:8081
- **CA**: https://storage.yandexcloud.net/cloud-certs/CA.pem

### Структура
```
kafka-demo/
  certs/CA.pem
  tools/client.properties
  schema-registry/etc/schema-registry/schema-registry.properties
  schema/app_event.avsc
  python/requirements.txt
  python/producer.py
  python/consumer.py
  logs/
```

### 1) Подготовка окружения (Ubuntu 22.04)
```bash
sudo apt-get update -y
sudo apt-get install -y openjdk-17-jre-headless python3-venv python3-pip jq curl

mkdir -p ~/kafka-demo/{schema,python,schema-registry,certs,tools,logs}
curl -sSLo ~/kafka-demo/certs/CA.pem https://storage.yandexcloud.net/cloud-certs/CA.pem
keytool -importcert -alias yandexcloud -file ~/kafka-demo/certs/CA.pem -keystore ~/kafka-demo/certs/yandex-truststore.jks -storepass trustpass -noprompt
wget -qO ~/kafka-demo/tools/confluent-7.6.1.tar.gz https://packages.confluent.io/archive/7.6/confluent-7.6.1.tar.gz
tar -xzf ~/kafka-demo/tools/confluent-7.6.1.tar.gz -C ~/kafka-demo/schema-registry --strip-components=1
```

### 2) Конфиг Schema Registry
Файл `schema-registry.properties` уже настроен на `schemas` и SASL_SSL (SCRAM-SHA-512). Ключевые параметры:
```ini
listeners=http://0.0.0.0:8081
kafkastore.bootstrap.servers=<3 брокера>:9091
kafkastore.topic=schemas
kafkastore.security.protocol=SASL_SSL
kafkastore.sasl.mechanism=SCRAM-SHA-512
kafkastore.sasl.jaas.config=... user123/password123 ...
kafkastore.ssl.truststore.location=~/kafka-demo/certs/yandex-truststore.jks
```

Запуск SR:
```bash
~/kafka-demo/schema-registry/bin/schema-registry-start ~/kafka-demo/schema-registry/etc/schema-registry/schema-registry.properties > ~/kafka-demo/logs/schema-registry.log 2>&1 &
sleep 5
curl -s http://localhost:8081/subjects | jq .
```

### 3) Регистрация схемы
```bash
jq -Rs '{schema: .}' ~/kafka-demo/schema/app_event.avsc > ~/kafka-demo/schema/register_payload.json
curl -s -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data @~/kafka-demo/schema/register_payload.json \
  http://localhost:8081/subjects/app.events-value/versions | jq .

curl -s http://localhost:8081/subjects | jq .
curl -s http://localhost:8081/subjects/app.events-value/versions | jq .
```

### 4) Проверка топика
```bash
~/kafka-demo/schema-registry/bin/kafka-topics --bootstrap-server rc1b-6v254d3mu3mlhcg5.mdb.yandexcloud.net:9091,rc1b-ga7q4l5c43kes7ms.mdb.yandexcloud.net:9091,rc1b-tl2r3tk8eaau7h4d.mdb.yandexcloud.net:9091 \
  --command-config ~/kafka-demo/tools/java-client.properties --describe --topic app.events | cat
```

### 5) Python окружение
```bash
cd ~/kafka-demo/python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 6) Тест продюсер/консьюмер
```bash
export KAFKA_USERNAME=user123 KAFKA_PASSWORD=password123 KAFKA_TOPIC=app.events SCHEMA_REGISTRY_URL=http://localhost:8081

python producer.py | tee ~/kafka-demo/logs/producer.log
python consumer.py | tee ~/kafka-demo/logs/consumer.log
```

Ожидаемое:
- `curl /subjects` содержит `app.events-value`
- версии схемы возвращаются `curl /subjects/app.events-value/versions`
- producer выводит Delivered ...
- consumer выводит Received ... с значениями

### Примечания по безопасности
- Для Kafka используется TLS (CA.pem) и SCRAM-SHA-512.
- Schema Registry хранит метаданные в топике `schemas` (RF=3).

