import pigpio

FAN_GPIO = 18
PWM_FREQ = 25000

pi = pigpio.pi()
if not pi.connected:
	print("Could not connect to pigpiod")
	exit(1)

print("Enter duty cycle % (0-100) or 'q' to quit")

try:
	while True:
		user = input("Enter duty cycle %: ")
		if user.lower() == 'q':
			break
		duty = float(user)
		if 0 <= duty <= 100:
			duty_hw = int(duty / 100 * 1_000_000)
			pi.hardware_PWM(FAN_GPIO, PWM_FREQ, duty_hw)
		else:
			print("Invalid percentage\n")

except KeyboardInterrupt:
	pass
finally:
	pi.hardware_PWM(FAN_GPIO, 0, 0)
	pi.stop()

