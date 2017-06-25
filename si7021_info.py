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
	print("   Device name: 0x{0:02X} ({1})".format(sn['device'], sn['device_str']))
	print("   Firmware version: 0x{0:02X} (v{1})".format(sn['fw'], sn['fw_str']))
	print("   Serial number: {0}".format(byte_array_to_string(sn['sn'])))
else:
	print("Errors occured.")
	print("Error code: {0}".format(sn["ok"]))
	if (sn["ok"] == 2):
		print("  Lengths returned: {0} {1} {2}".format(sn["sn"][0], sn["sn"][1], sn["sn"][2]))

print_config(si.ReadSettings())

# end.
