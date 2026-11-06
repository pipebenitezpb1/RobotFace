// Calibración del mecanismo de ojos con PCA9685.
// Control por monitor serie (115200 baudios), una orden por línea:
//   <canal> <angulo>   mueve un canal (0-15) a un ángulo (0-180). Ej: "2 90"
//   c                  centra los canales 0-5 en 90°
//   o                  apaga la señal de todos los servos (quedan sueltos)
//   s                  busca dispositivos en el bus I2C
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm(0x40);

const int PULSO_MIN = 600;   // µs a 0°
const int PULSO_MAX = 2400;  // µs a 180°
const int NUM_SERVOS = 6;

void moverServo(uint8_t canal, int angulo) {
  angulo = constrain(angulo, -10, 190);   // 500–2500 µs: los SG90 aguantan un poco más que 0–180°
  pwm.writeMicroseconds(canal, PULSO_MIN + (long)(PULSO_MAX - PULSO_MIN) * angulo / 180);
  Serial.print(F("OK canal "));
  Serial.print(canal);
  Serial.print(F(" -> "));
  Serial.println(angulo);
}

void escanearI2C() {
  int encontrados = 0;
  for (uint8_t dir = 1; dir < 127; dir++) {
    Wire.beginTransmission(dir);
    if (Wire.endTransmission() == 0) {
      Serial.print(F("I2C en 0x"));
      Serial.println(dir, HEX);
      encontrados++;
    }
  }
  if (encontrados == 0) Serial.println(F("I2C: nada encontrado"));
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  pwm.begin();
  pwm.setOscillatorFrequency(27000000);
  pwm.setPWMFreq(50);
  Serial.println(F("LISTO"));
  escanearI2C();
}

void loop() {
  if (!Serial.available()) return;
  String linea = Serial.readStringUntil('\n');
  linea.trim();
  if (linea.length() == 0) return;

  if (linea == "c") {
    for (uint8_t i = 0; i < NUM_SERVOS; i++) moverServo(i, 90);
  } else if (linea == "o") {
    for (uint8_t i = 0; i < 16; i++) pwm.setPWM(i, 0, 4096);
    Serial.println(F("OK servos apagados"));
  } else if (linea == "s") {
    escanearI2C();
  } else {
    int espacio = linea.indexOf(' ');
    if (espacio < 0) {
      Serial.println(F("ERROR orden desconocida"));
      return;
    }
    int canal = linea.substring(0, espacio).toInt();
    int angulo = linea.substring(espacio + 1).toInt();
    if (canal < 0 || canal > 15) {
      Serial.println(F("ERROR canal fuera de rango"));
      return;
    }
    moverServo(canal, angulo);
  }
}
