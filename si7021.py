#!/usr/bin/python3

# -*- coding: utf-8 -*-
"""Si7021 control class

Si7021 class is a helper to interface with Si7021 humidity and temperature sensor.
Class utilize PiGPIO library ( http://abyz.co.uk/rpi/pigpio/ ) so it must be installed beforehand.
Follow pigpio home page Download instruction to get it up and running ( http://abyz.co.uk/rpi/pigpio/download.html ).
pigpio was used because sensor Si7021 don't follow strictly SMBus spec for all commands, 
the pigpio provided good solution for dealing with i2c frames construction of si7021.

Check the code of si7021_test.py for reference.

Todo:
	* Check how calc of RH & temp is done after change of resolution
	* [Wishlist Feature] set heater register value from specified current in mA (0.01mA resolution)

Credists:
	Me - saper_2 / 2017-06-25 :D
	hippy from raspberrypi.org forum - crc8_update working code

License:
	MIT

"""

import time
import pigpio

def byte_array_to_string(ar):
	s = ""
	for a in ar:
		s += "{:02X} ".format(a)
	return s


class Si7021:
	def __init__(self, _piBus, _siAddr=0x40, _readMode=0):
		"""Initialize Si7021 interface class.
		
		Args:
			_piBus: Raspberry Pi I2C bus number
			_siAddr: Si7021 I2C address (0x40 default)
			_readMode: Measurement RH/Temp exec & read mode (only SI7021_READ_MODE_NO_HOLD supported)
		
		Returns:
			none
		"""
		self.piBus = int(_piBus)
		self.siAddr = int(_siAddr)
		self.pio = pigpio.pi()
		self.ReadMode = int(_readMode)
		self.HumiRes = 12
		self.TempRes = 14
		self.HeaterOn = 0
		self.HeaterVal = 0
	
	
	def __del__(self):
		self.pio.stop()		

	# Constans - Si7021 default I2C address
	SI7021_DEF_ADDR=0x40
	# Constans - Si7021 commands
	SI7021_CMD_MEAS_HUMI_HOLD_MASTER=0xE5
	SI7021_CMD_MEAS_HUMI_NOHOLD_MASTER=0xF5
	SI7021_CMD_MEAS_TEMP_HOLD_MASTER=0xE3
	SI7021_CMD_MEAS_TEMP_NOHOLD_MASTER=0xF3
	SI7021_CMD_READ_TEMP_LAST_HUMI=0xE0
	SI7021_CMD_RESET=0xFE
	SI7021_CMD_WRITE_USER=0xE6
	SI7021_CMD_READ_USER=0xE7
	SI7021_CMD_WRITE_HEATER=0x51
	SI7021_CMD_READ_HEATER=0x11
	SI7021_CMD_READ_EID1_1=0xFA
	SI7021_CMD_READ_EID1_2=0x0F
	SI7021_CMD_READ_EID2_1=0xFC
	SI7021_CMD_READ_EID2_2=0xC9
	SI7021_CMD_READ_FW_1=0x84
	SI7021_CMD_READ_FW_2=0xB8
	# Constans - Si7021 class ReadMode
	SI7021_READ_MODE_NO_HOLD=0
	
	def crc8_update(self, b, crc):
		"""CRC-8 calculation for polynomial x^8+x^5+x^4+1
		Polynomial is identical to Dallas/Maxim 1-Wire
		Working code thanks to hippy from raspberrypi.org forum
		
		Args:
			b: byte to compute crc from
			crc: byte with alredy computed crc that will be updated (or crc seed)

		Returns:
			Byte - crc value updated with 'b' byte
		"""
		for k in range(8):
			if ( ((b^crc) & 0x80) == 0x80 ):
				crc = crc<<1
				crc = crc^0x31
			else:
				crc = crc<<1
			b = b << 1
		crc = crc & 0xFF
		return crc
	
	def ReadSN(self):
		"""Read Si70xx serial number & firmware version and check CRC at the same time.
		Tested only on Si7021, so I don't know if other chips will follow data layout.

		Args:


		Returns:
			dict with fields:
				ok(int): 
					0=No errors, 
					1 or 2=Errors occured (CRC mismatch in 1=data1 or 2=data2), 
					3=Response lengths missmatch (sn[0..2] contains response lengths)
				sn(list[int]): list[len=8] of S/N bytes (SNA_3 .. SNA_0 , SNB_3 .. SNB_0 )
				fw(int): firmware version
				device(int): device model (SNB_3 field value)
				device_str(string): string with full device name
				fw_str(string): firmware version in string
		"""
		dev = self.pio.i2c_open(self.piBus, self.siAddr)
		# self.ReadMode == SI7021_READ_MODE_NO_HOLD
		(cnt1, dta1) = self.pio.i2c_zip(dev, [2, 4, self.siAddr, 7, 2, self.SI7021_CMD_READ_EID1_1, self.SI7021_CMD_READ_EID1_2, 6, 8, 0])
		
		(cnt2, dta2) = self.pio.i2c_zip(dev, [2, 4, self.siAddr, 7, 2, self.SI7021_CMD_READ_EID2_1, self.SI7021_CMD_READ_EID2_2, 6, 6, 0])
		(cnt3, dta3) = self.pio.i2c_zip(dev, [2, 4, self.siAddr, 7, 2, self.SI7021_CMD_READ_FW_1,   self.SI7021_CMD_READ_FW_2, 6, 1, 0])
		self.pio.i2c_close(dev)
		#print("SN:0:Count={0} RetData={1}".format(cnt1,byte_array_to_string(dta1)))
		#print("SN:1:Count={0} RetData={1}".format(cnt2,byte_array_to_string(dta2)))
		#print("FW:0:Count={0} RetData={1}".format(cnt3,byte_array_to_string(dta3)))
		if (cnt1 == 8 and cnt2 == 6 and cnt3 == 1):
			# check CRC of 1st data
			#print("Checking CRC8... ")
			crc=0x00 #init seed
			ok=0
			for i in range(4):
				b = dta1[i*2]
				bcrc = dta1[(i*2)+1]
				crc = self.crc8_update(b, crc)
				#print("  Data1[{0}]=0x{1:02X} CRC_GOT=0x{2:02X} CRC_CALC={3:02X} OK={4}".format(i*2, b, bcrc, crc, (bcrc==crc)))
				if (bcrc != crc):
					ok=1
					#print("  Data1[{0}]=0x{1:02X} CRC_GOT=0x{2:02X} CRC_CALC={3:02X} MATCH={4}".format(i*2, b, bcrc, crc, (bcrc==crc)))
			# check CRC of 2nd data
			crc=0x00 # init seed
			for i in range(2):
				b = dta2[(i*3)+0]
				c = dta2[(i*3)+1]
				bcrc = dta2[(i*3)+2]
				crc = self.crc8_update(b, crc)
				crc = self.crc8_update(c, crc)
				#print("  Data2[{0},{1}]=0x{2:02X},0x{3:02X} CRC_GOT=0x{4:02X} CRC_CALC={5:02X} MATCH={6}".format(i*3,(i*3)+1, b, c, bcrc, crc, (bcrc==crc)))
				if (bcrc != crc):
					ok=2
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
			# lengths mismatch
			#print("Expected 8, 6 and 1  bytes, but got: {0} {1} {2}".format(cnt1, cnt2, cnt3))
			#if (cnt1 > 0):
			#	print("  Data0[..]=", end=' ')
			#	for i in range(cnt1):
			#		print("{:02X} ".format(dta1[i]), end=' ')
			#	print(" ")
			#if (cnt2 > 0):
			#	print("  Data1[..]=", end=' ')
			#	for i in range(cnt2):
			#		print("{:02X} ".format(dta1[i]), end=' ')
			#	print(" ")
			#if (cnt3 > 0):
			#	print("  Data3[..]=", end=' ')
			#	for i in range(cnt3):
			#		print("{:02X} ".format(dta1[i]), end=' ')
			#	print(" ")
			re = {
				'ok': 3,
				'sn': [ cnt1, cnt2, cnt3, 0xff, 0xff, 0xff, 0xff, 0xff ],
				'device': 0xff,
				'device_str': "err_len_resp",
				'fw': 0x00,
				'fw_str': "Err"
				}
			return re

		# --------------
		# end func. - this return should never occur
		return { 'ok':255, 'sn': ([0xff]*8), 'device': 0xff, 'device_str': 'error', 'fw': 0x00, 'fw_str': 'err' }

	def Reset(self):
		"""Perform software reset to Si7021
		
		Args:
			
		Returns:
			
		"""
		dev = self.pio.i2c_open(self.piBus, self.siAddr)
		self.pio.i2c_write_byte(dev, self.SI7021_CMD_RESET); # CMD reset
		self.pio.i2c_close(dev)
		time.sleep(0.1) # wait 100ms (min 15ms)
		return
	
	def ReadSettings(self):
		"""Read Si7021 settings and pack them into nice dict :)
		
		Args:
			none
		
		Returns:
			dict with fields:
				user(int): RAW value of User register
				heater(int): RAW value of Heater register
				res(int): RES[1:0] bits
				vdds(int): VDDS bit (0=Vdd ok, 1=Low)
				vdds_str(string): VDDS status in string
				htre(int): HTRE bit - Heater enable (0=Off, 1=On)
				htre_str(string): HTRE bit in string ('On'/'Off')
				heater_curr(int): Calculated (aprox.) heater crrent in 0.01mA resolution (10uA)
				rh_res(int): Humidity measurement resolution (bits)
				temp_res(int): Temperature measurement resolution (bits)
		"""
		dev = self.pio.i2c_open(self.piBus, self.siAddr)
		ur = self.pio.i2c_read_byte_data(dev, self.SI7021_CMD_READ_USER) #Read User Register
		ht = self.pio.i2c_read_byte_data(dev, self.SI7021_CMD_READ_HEATER) #Read heater register
		self.pio.i2c_close(dev)
		#print("   User Register: 0x{0:02X} ({0:#010b})".format(ur))
		#print("   Heater register 0x{0:02X} ({0:#010b})".format(ht))
		# sampling resolution (Meas. res.)
		sr = ((ur&0x80)>>6) | (ur&0x01)
		rrh=12 # res. humi
		rtp=14 # res. temp
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
		# update class var.
		self.HumiRes = rrh
		self.TempRes = rtp
		self.HeaterOn = htre
		self.HeaterVal = ht
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
	
	
	def SetHeater(self, htrval):
		"""Set heater register value with 'htrval'
		
		Args:
			htrval(int): Heater current in binary value (0..15 = ~3.1mA .. ~94mA)
		
		Returns:
			True if register value match after write, false if not.
		"""
		htrval = htrval & 0x0F
		dev = self.pio.i2c_open(self.piBus, self.siAddr)
		self.pio.i2c_write_byte_data(dev, self.SI7021_CMD_WRITE_HEATER, htrval) #Write heater value
		time.sleep(0.01)
		# read back and check if match written value)
		ht = self.pio.i2c_read_byte_data(dev, self.SI7021_CMD_READ_HEATER) #Read heater register
		self.pio.i2c_close(dev)
		if (htrval==ht):
			self.HeaterVal=htrval
		else:
			self.HeaterVal=ht&0x0F

		return (htrval==ht)

	def GetHeaterCurrent(self, hreg=-1):
		"""Return approx. heater current from heater register value
		
		Args:
			hreg(int): Heater register value (0..15) , if ommited (or -1) then value will be used from last settings read or SetHeater
		
		Returns:
			int:Approx. heater current in 0.01mA resolution (10uA)
		"""
		# if hreg==-1 then grab hreg value from last read/set heater		
		if (hreg < 0): hreg=self.HeaterVal
		hreg &= 0x0F # mask MSB nibble		
		hcc = (-299)+((hreg+1)*608)
		return hcc

	def SetSampling(self, val):
		"""Set measurement resolution (RES[1:0] bits)
		
		Args:
			val (int): RES[1:0] bits value (0x00..0x03 ; val[0]=RES0 , val[1]=RES1)

		Returns:
			True if RESx bit set OK, otherwise false.
		"""
		val = val & 0x03
		dev = self.pio.i2c_open(self.piBus, self.siAddr)
		ur = self.pio.i2c_read_byte_data(dev, self.SI7021_CMD_READ_USER) #Read User Register
		# mask RES[1:0] bits
		ur &= 0x7e
		# set new bits values - the hard way :D
		ur |= ((val&0x02)<<6) | (val&0x01)
		# easier way is to use if's for val bits, then in-if set matching bits in ur
		self.pio.i2c_write_byte_data(dev, self.SI7021_CMD_WRITE_USER, ur) #Write user value back with moddified bits
		time.sleep(0.01) # wait a moment
		# read back ur and check if match
		ur2 = self.pio.i2c_read_byte_data(dev, self.SI7021_CMD_READ_USER) #Read User Register
		self.pio.i2c_close(dev)
		if (ur==ur2):
			# update class vars
			rrh=12
			rtp=14
			sr=val
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
			self.HumiRes=rrh
			self.TempRes=rtp
		return (ur==ur2)
	
	
	def MeasHumi(self):
		"""
		Perform Humidity (and temperature) measurement.
		This use 'NO HOLD MASTER' mode. 
		The conversion result after issuing command is read back after delay of 30ms.
		Minimum safe time is about 12ms according to datasheet but 30ms seems to be safer :)
		
		Args:
			
		Returns:
			RH value (int) in 0.01% resolution.
			To get value with 'decimal part' just div it by 100.0
		""" 
		dev = self.pio.i2c_open(self.piBus, self.siAddr)
		self.pio.i2c_write_byte(dev, self.SI7021_CMD_MEAS_HUMI_NOHOLD_MASTER)
		time.sleep(0.03) # min. about 12ms for humi
		(cnt, dta) = self.pio.i2c_read_device(dev, 2) # get 2 bytes
		self.pio.i2c_close(dev)
		rh_code = ((dta[0]<<8)&0xff00) | dta[1]
		rh = ((125*rh_code)/65536) - 6
		rh = rh * 100
		rhi = int(round(rh))
		return rhi	
	
	def MeasTemp(self):
		"""
		Perform Temperature measurement.
		This use 'NO HOLD MASTER' mode.
		The conversion result after issuing command is read back after delay of 20ms.
		Minimum safe time is about 11ms according to datasheet but 20ms seems to be safer :)

		Args:

		Returns:
			Temperature value (int) in 0.01degC resolution.
			To get value with 'decimal part' just div it by 100.0
		"""
		dev = self.pio.i2c_open(self.piBus, self.siAddr)
		self.pio.i2c_write_byte(dev, self.SI7021_CMD_MEAS_TEMP_NOHOLD_MASTER)
		time.sleep(0.02) # min. about 11ms for temp.
		(cnt, dta) = self.pio.i2c_read_device(dev, 2)
		self.pio.i2c_close(dev)
		temp_code = ((dta[0]<<8)&0xff00) | dta[1]
		temp = ((175.72*temp_code)/65536) - 46.85
		temp = temp * 100
		tempi = int(round(temp))
		return tempi
	
	
	def GetLastMeasHumiTemp(self):
		"""Read temperature from last humidity measurement.
		(FYI: To measure humidity sensor must measure temperature too.)
		
		Args:

		Returns:
			Temperature value (int) in 0.01degC resolution.
			To get value with 'decimal part' just div it by 100.0
		"""
		dev = self.pio.i2c_open(self.piBus, self.siAddr)
		self.pio.i2c_write_byte(dev, self.SI7021_CMD_READ_TEMP_LAST_HUMI)
		time.sleep(0.01)
		(cnt, dta) = self.pio.i2c_read_device(dev, 2)
		self.pio.i2c_close(dev)
		temp_code = ((dta[0]<<8)&0xff00) | dta[1]
		temp = ((175.72*temp_code)/65536) - 46.85
		temp = temp * 100
		tempi = int(round(temp))
		return tempi

	def MeasHumiTemp(self):
		"""Combined version of MeasHumi and GetLastMeasHumiTemp .
		
		Args:

		Returns:
			dict with 2 fileds, one for humi another for temp:
				humi(int): Humidity in 0.01% resolution
				temp(int): Temperature in 0.01degC resolution
			To get value with 'decimal part' just div it by 100.0
		"""
		rh = self.MeasHumi()
		tp = self.GetLastMeasHumiTemp()
		return { "humi": rh, "temp": tp }

	


