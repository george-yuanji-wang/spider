#include <pwmWrite.h>

#define ENA         7
#define IN1         6
#define IN2         5
#define IN3         4
#define IN4         3
#define ENB         2
#define SERVO_PIN   9

#define PWM_FREQ        2000
#define PWM_RES         8
#define ENA_CH          2
#define ENB_CH          3

#define MOTOR_PWM_MIN   100
#define MOTOR_PWM_MAX   255

#define LEFT_FWD_POLARITY   true
#define RIGHT_FWD_POLARITY  true

#define SERVO_ANGLE_0   70
#define SERVO_ANGLE_1   0
#define SERVO_STEP      3

#define SERIAL_TIMEOUT_MS   500

Pwm pwm = Pwm();
float servoPos    = SERVO_ANGLE_0;
float servoTarget = SERVO_ANGLE_0;
unsigned long lastReceived = 0;
bool safed = false;

void shutdownMotors() {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, LOW);
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, LOW);
    ledcWrite(ENA_CH, 0);
    ledcWrite(ENB_CH, 0);
}

void setMotor(int ch, int pinA, int pinB, bool fwdPolarity, int val) {
    val = constrain(val, -100, 100);
    if (val == 0) { digitalWrite(pinA, LOW); digitalWrite(pinB, LOW); ledcWrite(ch, 0); return; }
    bool forward = (val >= 0) ? fwdPolarity : !fwdPolarity;
    int pwmVal = map(abs(val), 1, 100, MOTOR_PWM_MIN, MOTOR_PWM_MAX);
    digitalWrite(pinA, forward ? HIGH : LOW);
    digitalWrite(pinB, forward ? LOW : HIGH);
    ledcWrite(ch, pwmVal);
}

void safeState() {
    shutdownMotors();
    servoTarget = SERVO_ANGLE_0;
}

void setup() {
    Serial.begin(115200);
    Serial.setTimeout(50);
    pinMode(IN1, OUTPUT);
    pinMode(IN2, OUTPUT);
    pinMode(IN3, OUTPUT);
    pinMode(IN4, OUTPUT);
    ledcSetup(ENA_CH, PWM_FREQ, PWM_RES);
    ledcSetup(ENB_CH, PWM_FREQ, PWM_RES);
    ledcAttachPin(ENA, ENA_CH);
    ledcAttachPin(ENB, ENB_CH);
    pwm.writeServo(SERVO_PIN, (int)servoPos);
    safeState();
    lastReceived = millis();
}

void loop() {
    if (abs(servoTarget - servoPos) > 0.5) {
        servoPos += (servoPos < servoTarget) ? SERVO_STEP : -SERVO_STEP;
        pwm.writeServo(SERVO_PIN, (int)servoPos);
        delay(10);
    }

    if (millis() - lastReceived > SERIAL_TIMEOUT_MS) {
        if (!safed) { safeState(); safed = true; }
    }

    if (!Serial.available()) return;
    String line = Serial.readStringUntil('\n');
    line.trim();
    int c1 = line.indexOf(',');
    int c2 = line.indexOf(',', c1 + 1);
    int c3 = line.indexOf(',', c2 + 1);
    if (c1 < 0 || c2 < 0 || c3 < 0) return;
    String s0 = line.substring(0, c1);
    String s1 = line.substring(c1 + 1, c2);
    String s2 = line.substring(c2 + 1, c3);
    String s3 = line.substring(c3 + 1);
    if (s0.length() == 0 || s1.length() == 0 || s2.length() == 0 || s3.length() == 0) return;
    int lm = s0.toInt();
    int rm = s1.toInt();
    int sv = s2.toInt();
    int en = s3.toInt();
    if (en == 0) { shutdownMotors(); }
    else {
        setMotor(ENA_CH, IN1, IN2, LEFT_FWD_POLARITY,  lm);
        setMotor(ENB_CH, IN3, IN4, RIGHT_FWD_POLARITY, rm);
    }
    servoTarget = (sv == 0) ? SERVO_ANGLE_0 : SERVO_ANGLE_1;
    lastReceived = millis();
    safed = false;
}