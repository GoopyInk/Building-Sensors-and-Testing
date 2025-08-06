import sqlite3
connection = sqlite3.connect("Sensor.db")
cursor = connection.cursor()
cursor.execute("CREATE TABLE CO2_Sensor(time FLOAT, int_10 INT)")
cursor.close()
connection.close()
print("created database")
