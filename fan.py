import RPi.GPIO as GPIO
import time
 
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)

p = GPIO.PWM(18, 2000)  
p.start(0)  

try:
    while True:
        speed = input("Enter fan speed (0-100) or 'q' to quit: ")

        if speed.lower() == 'q':
            break  # Exit loop on 'q'
        
        try:
            duty_cycle = float(speed)
            if 0 <= duty_cycle <= 100:
                p.ChangeDutyCycle(duty_cycle)
                print(f"Fan speed set to {duty_cycle}%")
            else:
                print("Please enter a value between 0 and 100.")
        except ValueError:
            print("Invalid input. Enter a number between 0 and 100 or 'q' to quit.")

except KeyboardInterrupt:
    pass

p.ChangeDutyCycle(0)
p.stop()
GPIO.cleanup()
