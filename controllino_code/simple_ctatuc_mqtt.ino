#include <SPI.h>
#include <Controllino.h>
#include <Ethernet.h>
#include <+.h>

// Enter a MAC address and IP address for your controller below.
// The IP address will be dependent on your local network.
// gateway and subnet are optional:
byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };

IPAddress ip(10, 0, 1, 177);
IPAddress subnet(255, 255, 254, 0);
IPAddress gateway(10, 0, 1, 254);
IPAddress myDns(10, 0, 1, 254);

const char broker[] = "10.0.1.17";
int port = 1883;
const char topic[] = "sensor/c-leuse/status";

//set interval for sending messages (milliseconds)
const long interval = 8000;
unsigned long previousMillis = 0;

int count = 0;
EthernetClient ethernet;
MqttClient mqttClient(ethernet);

const int greenPin = CONTROLLINO_A9;
const int yellowPin = CONTROLLINO_A8;
const int redPin = CONTROLLINO_A7;


void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ;  // wait for serial port to connect. Needed for native USB port only
  }
  // put your setup code here, to run once:
  pinMode(greenPin, INPUT);
  pinMode(yellowPin, INPUT);
  pinMode(redPin, INPUT);
  Serial.println("Starting Ethernet ...");
  Ethernet.begin(mac, ip, myDns, gateway, subnet);

  if (Ethernet.linkStatus() == LinkOFF) {
    Serial.println("Ethernet cable is not connected.");
  }

  Serial.print("Ethernet IP address: ");
  Serial.println(Ethernet.localIP());

  Serial.print("Attempting to connect to the MQTT broker: ");
  Serial.println(broker);

  if (!mqttClient.connect(broker, port)) {
    Serial.print("MQTT connection failed! Error code = ");
    Serial.println(mqttClient.connectError());
    while (1)
      ;
  }

  Serial.println("You're connected to the MQTT broker!");
  Serial.println();
}

void loop() {
  // call poll() regularly to allow the library to send MQTT keep alive which
  // avoids being disconnected by the broker
  mqttClient.poll();

  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    String value = String("unknown");

    int green = analogRead(greenPin);
    int yellow = analogRead(yellowPin);
    int red = analogRead(redPin);

    if (green > 10) {
      value = String("open");
    } else if (yellow > 10) {
      value = String("shields_up");
    } else if (red > 10) {
      value = String("shutdown");
    }

    Serial.print("Sending message to topic: ");
    Serial.println(topic);
    Serial.println(value);

    // send message, the Print interface can be used to set the message contents
    mqttClient.beginMessage(topic);
    mqttClient.print(value);
    mqttClient.endMessage();

    Serial.println();
  }
}

