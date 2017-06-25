#!/usr/bin/python3

import time
import pigpio

#bus = smbus.SMBus(1)
pig = pigpio.pi()

SI7021_ADDR=0x40
SI7021_RES_RH12_TEMP14=0x00
SI7021_RES_RH8_TEMP12 =0x01
SI7021_RES_RH10_TEMP13=0x02
SI7021_RES_RH11_TEMP11=0x03

#bus.write_byte_data(SI7021_ADDR, 0xFA, 0x0F);
#dta = bus.read_block_data(SI7021_ADDR, 0x0FFA)
# crc8 calc by hippy@forum.raspberrypi.org - THX
def crc8_update(b, crc):
	for i in range(8):
		if ( ((b^crc) & 0x80) == 0x80 ):
			crc = crc<<1
			crc = crc^0x31
		else:
			crc = crc<<1
		b = b << 1
	
	crc = crc & 0xFF
	return crc


def byte_array_to_string(ar):
	s = ""
	for a in ar:
		s += "{:02X} ".format(a)
	return s


def si7021_read_sn():
	"""Read Si70xx serial number & firmware version and check CRC by doing it.
	Test only on Si7021, so I don't know if other chips will follow data layout.
	
	Args:

	Returns:
		dict with fields:
			ok(int): 1=No errors, 0=Errors occured (CRC mismatch somewhere)
			sn(list[int]): list[len=8] of S/N bytes (SNA_3 .. SNA_0 , SNB_3 .. SNB_0 )
			fw(int): firmware version 
			device(int): device model (SNB_3 field value)
			device_str(string): string with full device name
			fw_str(string): firmware version in string

	"""
	dev = pig.i2c_open(1, SI7021_ADDR)
	(cnt1, dta1) = pig.i2c_zip(dev, [2, 4, SI7021_ADDR, 7, 2, 0xFA, 0x0F, 6, 8, 0])
	(cnt2, dta2) = pig.i2c_zip(dev, [2, 4, SI7021_ADDR, 7, 2, 0xFC, 0xC9, 6, 6, 0])
	(cnt3, dta3) = pig.i2c_zip(dev, [2, 4, SI7021_ADDR, 7, 2, 0x84, 0xB8, 6, 1, 0])
	pig.i2c_close(dev)
	#print("SN:0:Count={0} RetData={1}".format(cnt1,byte_array_to_string(dta1)))
	#print("SN:1:Count={0} RetData={1}".format(cnt1,byte_array_to_string(dta2)))
	#print("FW:0:Count={0} RetData={1}".format(cnt3,byte_array_to_string(dta3)))
	if (cnt1 == 8 and cnt2 == 6 and cnt3 == 1):
		# check CRC of 1st data
		#print("Checking CRC8... ")
		crc=0x00 #init seed
		ok=1
		for i in range(4):
			b = dta1[i*2]
			bcrc = dta1[(i*2)+1]
			crc = crc8_update(b, crc)
			#print("  Data1[{0}]=0x{1:02X} CRC_GOT=0x{2:02X} CRC_CALC={3:02X} OK={4}".format(i*2, b, bcrc, crc, (bcrc==crc)))
			if (bcrc != crc):
				ok=0
				print("  Data1[{0}]=0x{1:02X} CRC_GOT=0x{2:02X} CRC_CALC={3:02X} MATCH={4}".format(i*2, b, bcrc, crc, (bcrc==crc)))
		# check CRC of 2nd data
		crc=0 # init seed
		for i in range(2):
			b = dta2[(i*3)+0]
			c = dta2[(i*3)+1]
			bcrc = dta2[(i*3)+2]
			crc = crc8_update(b, crc)
			crc = crc8_update(c, crc)
			#print("  Data2[{0},{1}]=0x{2:02X},0x{3:02X} CRC_GOT=0x{4:02X} CRC_CALC={5:02X} MATCH={6}".format(i*3,(i*3)+1, b, c, bcrc, crc, (bcrc==crc)))
			if (bcrc != crc):
				ok=0
				#print("  Data2[{0},{1}]=0x{2:02X},0x{3:02X} CRC_GOT=0x{4:02X} CRC_CALC={5:02X} MATCH={6}".format(i*3,(i*3)+1, b, c, bcrc, crc, (bcrc==crc))) 
		# 3rd data don't need nor have CRC so - nothing to do :)
		# ------- now reassemble all important data into nice dict :)
		# device name string
		dn="Unknown_Si70_{0}".format(dta2[0])
		if (dta2[0] == 0x00 or dta2[0] == 0xff):
			dn="Samples"
		elif (dta2[0] == 0x0d):
			dn="Si7013"
		elif (dta2[0] == 0x14):
			dn="Si7020"
		elif (dta2[0] == 0x15):
			dn="Si7021"
		# firmware version
		fws="Unknown_{:#02X}".format(dta3[0])
		if (dta3[0] == 0xFF):
			fws="1.0"
		elif (dta3[0] == 0x20):
			fws="2.0"
		# build return data
		re = { 
			'ok': ok, 
			'sn': [ dta1[0], dta1[2], dta1[4], dta1[6], dta2[0], dta2[1], dta2[3], dta2[4] ], 
			'device': dta2[0], 
			'device_str': dn,
			'fw': dta3[0],
			'fw_str': fws
			}
		return re
			
			
	else:
		print("Expected 8, 6 and 1  bytes, but got: {0} {1} {2}".format(cnt1, cnt2, cnt3))
		if (cnt1 > 0):
			print("  Data0[..]=", end=' ')
			for i in range(cnt1):
				print("{:02X} ".format(dta1[i]), end=' ')
			print(" ")
		if (cnt2 > 0):
			print("  Data1[..]=", end=' ')
			for i in range(cnt2):
				print("{:02X} ".format(dta1[i]), end=' ')
			print(" ")
		if (cnt3 > 0):
			print("  Data3[..]=", end=' ')
			for i in range(cnt3):
				print("{:02X} ".format(dta1[i]), end=' ')
			print(" ")
	# --------------
	# end func.
	return { 'ok':0, 'sn': ([0xff]*8), 'device': 0xff, 'device_str': 'error', 'fw': 0x00, 'fw_str': 'err' }
	

def si7021_reset():
	dev = pig.i2c_open(1, SI7021_ADDR)
	pig.i2c_write_byte(dev, 0xFE); # CMD reset
	pig.i2c_close(dev)
	time.sleep(0.03) # wait 30ms (min 15ms)
	return


def si7021_read_settings():
	dev = pig.i2c_open(1, SI7021_ADDR)
	ur = pig.i2c_read_byte_data(dev, 0xE7) #Read User Register
	ht = pig.i2c_read_byte_data(dev, 0x11) #Read heater register
	pig.i2c_close(dev)
	print("   User Register: 0x{0:02X} ({0:#010b})".format(ur))
	print("   Heater register 0x{0:02X} ({0:#010b})".format(ht))
	# sampling resolution (Meas. res.)
	sr = ((ur&0x80)>>6) | (ur&0x01)
	rrh=12
	rtp=14
	if (sr == 0x00):
		rrh=12
		rtp=14
	elif (sr == 0x01):
		rrh=8
		rtp=12
	elif (sr == 0x02):
		rrh=10
		rtp=13
	elif (sr == 0x03):
		rrh=11
		rtp=11
	# vdd status
	vdds = (ur&40)>>6
	# heater on
	htre = (ur&0x04)>>2
	# heater value
	ht = ht&0x0f
	# heater current in 0.01mA
	htc = (-299)+((ht+1)*608)
	# vdd status string
	vddstr="Low"
	if (vdds == 0): vddstr="OK"
	# heater status string
	htrestr="Off"
	if (htre == 1): htrestr="On"
	# return dict
	re = {
		'user': ur,
		'heater': ht,
		'res': sr,
		'vdds': vdds,
		'vdds_str': vddstr,
		'htre': htre,
		'htre_str': htrestr,
		'heater_curr': htc,
		'rh_res': rrh,
		'temp_res': rtp
	}	
	return re
	

def si7021_set_heater(htrval):
	htrval = htrval & 0x0F
	dev = pig.i2c_open(1, SI7021_ADDR)
	pig.i2c_write_byte_data(dev, 0x51, htrval) #Write heater value
	time.sleep(0.01)
	# read back and check if match written value)
	ht = pig.i2c_read_byte_data(dev, 0x11) #Read heater register
	pig.i2c_close(dev)
	return (htrval==ht)


def si7021_set_sampling(val):
	val = val & 0x03
	dev = pig.i2c_open(1, SI7021_ADDR)
	ur = pig.i2c_read_byte_data(dev, 0xE7) #Read User Register
	# mask RES[1:0] bits
	ur &= 0x7e
	# set new bits values - the hard way :D
	ur |= ((val&0x02)<<6) | (val&0x01)
	# easier way is to use if's for val bits, then in-if set matching bits in ur
	pig.i2c_write_byte_data(dev, 0xE6, ur) #Write user value back with moddified bits
	time.sleep(0.01) # wait a moment
	# read back ur and check if match
	ur2 = pig.i2c_read_byte_data(dev, 0xE7) #Read User Register
	pig.i2c_close(dev)
	return (ur==ur2)


def si7021_meas_humi(bits=12):
	dev = pig.i2c_open(1, SI7021_ADDR)
	pig.i2c_write_byte(dev, 0xF5)
	time.sleep(0.03) # min. about 12ms for humi
	(cnt, dta) = pig.i2c_read_device(dev, 2)
	pig.i2c_close(dev)
	rh_code = ((dta[0]<<8)&0xff00) | dta[1]
	rh = ((125*rh_code)/65536) - 6
	rh = rh * 100
	rhi = int(round(rh))
	return rhi


def si7021_read_temp_last_humi():
	dev = pig.i2c_open(1, SI7021_ADDR)
	pig.i2c_write_byte(dev, 0xE0)
	time.sleep(0.01)
	(cnt, dta) = pig.i2c_read_device(dev, 2)
	pig.i2c_close(dev)
	temp_code = ((dta[0]<<8)&0xff00) | dta[1]
	temp = ((175.72*temp_code)/65536) - 46.85
	temp = temp * 100
	tempi = int(round(temp))
	return tempi


def si7021_meas_temp(bits=14):
	dev = pig.i2c_open(1, SI7021_ADDR)
	pig.i2c_write_byte(dev, 0xF3)
	time.sleep(0.02) # min. about 11ms for temp.
	(cnt, dta) = pig.i2c_read_device(dev, 2)
	pig.i2c_close(dev)
	temp_code = ((dta[0]<<8)&0xff00) | dta[1]
	temp = ((175.72*temp_code)/65536) - 46.85
	temp = temp * 100
	tempi = int(round(temp))
	return tempi


# ---------------------------------------------------
def read_and_print_config():
	print("Reading Si7021 configruation...")
	sett=si7021_read_settings()
	print("   Measurement resolution: RH={0}bit TEMP={1}bit (RES[1:0]=0x{2:02X})".format(sett['rh_res'],sett['temp_res'],sett['res']))
	print("   Vdd status: 0x{0:02X} ({1})".format(sett["vdds"],sett["vdds_str"]))
	print("   Heater status: 0x{0:02X} ({1})".format(sett['htre'],sett['htre_str']))
	print("   Heater current: 0x{0:02X} ({1:4.2f}mA)".format(sett["heater"],sett["heater_curr"]*0.01))
	print("   User register RAW value: 0x{0:02X} ({0:#010b})".format(sett["user"]))
	return

# ***********************************************
print("Issuing reset to Si7021...")
si7021_reset()
print("Reading S/N & F/W...", end=' ')
sn = si7021_read_sn()
if (sn['ok'] == 1):
	print(" Success.")
	print("   Device name: 0x{0:02X} ({1})".format(sn['device'], sn['device_str']))
	print("   Firmware version: 0x{0:02X} (v{1})".format(sn['fw'], sn['fw_str']))
	print("   Serial number: {0}".format(byte_array_to_string(sn['sn'])))
else:
	print("Errors occured.")
read_and_print_config()
print("----------------------------")
print("Testing functions...")
print("Set heater ~57.8mA...", end=" ")
print(si7021_set_heater(0x09))
read_and_print_config()
print("---------")
print("Set sampling RH=11b Temp=11b (0b1xxxxxx1)... {0}".format(si7021_set_sampling(0x03)))
read_and_print_config()
print("---------")
print("Reset...")
si7021_reset()
read_and_print_config()
print("+++++++++++++")
print("Measuring RH... {0:6.4f}%".format(si7021_meas_humi()/100.0))
print("Temparature of last RH sampling... {0:6.4f}degC".format(si7021_read_temp_last_humi()/100.0))
print("Measuring Temperature... {0:6.4f}degC".format(si7021_meas_temp()/100.0))

print("Reading RH & Temp. in loop until script will be terminated...")

try:
	while True:
		rh = si7021_meas_humi()/100.0
		tp = si7021_read_temp_last_humi()/100.0
		print("Read RH={0:4.2f}% TEMP={1:4.2f}degC".format(rh,tp))
		time.sleep(1.0)
except KeyboardInterrupt:
	pass


 


pig.stop()

