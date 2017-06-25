#!/usr/bin/python3

from si7021 import Si7021
import time

# helper functions
def byte_array_to_string(ar):
	s = ""
	for a in ar:
		s += "{:02X} ".format(a)
	return s

def print_config(sett):
	print("Reading Si7021 configruation...")
	print("   Measurement resolution: RH={0}bit TEMP={1}bit (RES[1:0]=0x{2:02X})".format(sett['rh_res'],sett['temp_res'],sett['res']))
	print("   Vdd status: 0x{0:02X} ({1})".format(sett["vdds"],sett["vdds_str"]))
	print("   Heater status: 0x{0:02X} ({1})".format(sett['htre'],sett['htre_str']))
	print("   Heater current: 0x{0:02X} ({1:4.2f}mA)".format(sett["heater"],sett["heater_curr"]*0.01))
	print("   User register RAW value: 0x{0:02X} ({0:#010b})".format(sett["user"]))
	return

# -----------------------------------------------------

print("Init si7021 class...")
si = Si7021(1,Si7021.SI7021_DEF_ADDR)

print("Issuing reset to Si7021...")
si.Reset()

print("Reading S/N & F/W...", end=' ')
sn = si.ReadSN()
if (sn['ok'] == 0):
	print(" Success.")
	print("   Device name: {0:#02X} ({1})".format(sn['device'], sn['device_str']))
	print("   Firmware version: {0:#02X} (v{1})".format(sn['fw'], sn['fw_str']))
	print("   Serial number: {0}".format(byte_array_to_string(sn['sn'])))
else:
	print("Errors occured.")
	print("Error code: {0}".format(sn["ok"]))
	if (sn["ok"] == 2):
		print("  Lengths returned: {0} {1} {2}".format(sn["sn"][0], sn["sn"][1], sn["sn"][2]))

print_config(si.ReadSettings())
print("----------------------------")
print("Testing functions...")
print("Set heater ~57.8mA (0x09)...", end=" ")
print(si.SetHeater(0x09))
print_config(si.ReadSettings())
print("---------")
print("Set sampling RH=11bit Temp=11bit (0b1xxxxxx1)... {0}".format(si.SetSampling(0x03)))
print_config(si.ReadSettings())
print("---------")
print("Reset...")
si.Reset()
print_config(si.ReadSettings())
print("+++++++++++++")
print("Measuring RH... {0:6.4f}%".format(si.MeasHumi()/100.0))
print("Temparature of last RH sampling... {0:6.4f}degC".format(si.GetLastMeasHumiTemp()/100.0))
print("Measuring Temperature... {0:6.4f}degC".format(si.MeasTemp()/100.0))

print("Reading RH & Temp. in loop until script will be terminated...")


try:
	while True:
		rht = si.MeasHumiTemp()
		rh = rht["humi"]/100.0
		tp = rht["temp"]/100.0
		print("Read RH={0:4.2f}% TEMP={1:4.2f}degC".format(rh,tp))
		time.sleep(1.0)
except KeyboardInterrupt:
	pass

# end.
