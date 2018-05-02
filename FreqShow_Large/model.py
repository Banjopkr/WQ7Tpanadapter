# FreqShow main application model/state.
# Author: Tony DiCola (tony@tonydicola.com)
#
# The MIT License (MIT)
#
# Copyright (c) 2014 Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# Enhancements over the original Freqshow by Dan Stixrud, WQ7T
import numpy as np
from scipy import signal
from scipy.fftpack import fft, rfft, fftshift

from rtlsdr import *

import freqshow


class FreqShowModel(object):
	def __init__(self, width, height):
		"""Create main FreqShow application model.  Must provide the width and
		height of the screen in pixels.
		"""
		# Set properties that will be used by views.
		self.width = width
		self.height = height

		# Initialize auto scaling both min and max intensity (Y axis of plots).
		self.min_auto_scale = True
		self.max_auto_scale = True

		self.set_min_intensity(-10)
		self.set_max_intensity(50)

		# Initialize RTL-SDR library.
		self.sdr = RtlSdr()
                self.set_freq_correction(0)  # (58ppm for unenhanced)can run test to determine this value, via regular antenna, not IF frequency!
		self.set_swap_iq(True)   
                self.set_sample_rate(.230)  # in MHz, must be within (.225001 <= sample_rate_mhz <= .300000) OR (.900001 <= sample_rate_mhz <= 3.200000)
                self.set_zoom_fac(.05)   # equal to the frequency span you want to display on the screen in MHz
		self.set_lo_offset(0.03) # Local Oscillator offset in MHz, slide the DC spike out of the window by this amount.
		self.set_center_freq(70.451500)
 		self.set_gain('AUTO')
		self.set_fft_ave(3)
		self.set_tune_rate(.001) # in MHz   
		self.set_sig_strength(0.00)
		self.set_kaiser_beta(8.6)
		self.set_peak(True)   # Set true for peaks, set False for averaging. 	
		self.set_filter('nuttall') # set default windowing filter.


	def _clear_intensity(self):
		if self.min_auto_scale:
			self.min_intensity = None
		if self.max_auto_scale:
			self.max_intensity = None
		self.range = None

	def get_swap_iq(self):
		return (self.swap_iq)

	def set_swap_iq(self, swap_iq):
		self.swap_iq = (swap_iq)


        def get_peak(self):
                return (self.peak)

        def set_peak(self, peak):
                self.peak = (peak)


	def get_freq_correction(self):
#		return self.sdr.get_freq_correction()
		return (self.freq_correction)

	def set_freq_correction(self, freq_correction):
		self.freq_correction = (freq_correction)
		self.sdr.set_freq_correction(int(freq_correction+1))

        def get_lo_offset(self):
                return (self.lo_offset)


        def set_lo_offset(self, lo_offset):
                self.lo_offset = float(lo_offset)


	def get_center_freq(self):
		return (self.center_freq)

	def set_center_freq(self, value):
		self.center_freq  = (value)
		if ((self.get_sample_rate()/self.get_zoom_fac())/2)>((self.get_lo_offset()/self.get_zoom_fac())-(self.get_zoom_fac()/2)):
			freq_hz = float((self.get_center_freq() + self.get_lo_offset())*1000000)
		else:
			freq_hz = float(self.get_center_freq()*1000000)
		self.sdr.set_center_freq(float(freq_hz))
		self._clear_intensity()

	def get_lo_freq(self):
		"""Return center frequency of tuner in megahertz."""
		return (self.sdr.get_center_freq()/(1000000.0))
	
#	def set_lo_freq(self, freq_mhz):
#		"""Set tuner center frequency to provided megahertz value."""
#		try:	
#			self.sdr.set_center_freq(freq_mhz*(1000000.0))
#			self._clear_intensity()
#		except IOError:
#			# Error setting value, ignore it for now but in the future consider
#			# adding an error message dialog.
#			pass	

	def get_sample_rate(self):
		"""Return sample rate of tuner in megahertz."""
		return self.sdr.get_sample_rate()/1000000.0

	def set_sample_rate(self, sample_rate_mhz):
		"""Set tuner sample rate to provided frequency in megahertz."""
		if .225001 <= sample_rate_mhz <= .300000 or .900001 <= sample_rate_mhz <= 3.200000:
 			try:
				self.sdr.set_sample_rate(sample_rate_mhz*1000000.0)
			except IOError:
				# Error setting value, ignore it for now but in the future consider
				# adding an error message dialog.
				pass
		else:
			self.sample_rate = self.get_sample_rate()			

	def get_gain(self):
		"""Return gain of tuner.  Can be either the string 'AUTO' or a numeric
		value that is the gain in decibels.
		"""
		if self.auto_gain:
			return 'AUTO'
		else:
			return '{0:0.1f}'.format(self.sdr.get_gain())

	def set_gain(self, gain_db):
		"""Set gain of tuner.  Can be the string 'AUTO' for automatic gain
		or a numeric value in decibels for fixed gain.
		"""
		if gain_db == 'AUTO':
			self.sdr.set_manual_gain_enabled(False)
			self.auto_gain = True
			self._clear_intensity()
		else:
			try:
				self.sdr.set_gain(float(gain_db))
				self.auto_gain = False
				self._clear_intensity()
			except IOError:
				# Error setting value, ignore it for now but in the future consider
				# adding an error message dialog.
				pass

	def get_min_string(self):
		"""Return string with the appropriate minimum intensity value, either
		'AUTO' or the min intensity in decibels (rounded to no decimals).
		"""
		if self.min_auto_scale:
			return 'AUTO'
		else:
			return '{0:0.0f}'.format(self.min_intensity)

	def set_min_intensity(self, intensity):
		"""Set Y axis minimum intensity in decibels (i.e. dB value at bottom of 
		spectrograms).  Can also pass 'AUTO' to enable auto scaling of value.
		"""
		if intensity == 'AUTO':
			self.min_auto_scale = True
		else:
			self.min_auto_scale = False
			self.min_intensity = float(intensity)
		self._clear_intensity()

	def get_max_string(self):
		"""Return string with the appropriate maximum intensity value, either
		'AUTO' or the min intensity in decibels (rounded to no decimals).
		"""
		if self.max_auto_scale:
			return 'AUTO'
		else:
			return '{0:0.0f}'.format(self.max_intensity)

	def set_max_intensity(self, intensity):
		"""Set Y axis maximum intensity in decibels (i.e. dB value at top of 
		spectrograms).  Can also pass 'AUTO' to enable auto scaling of value.
		"""
		if intensity == 'AUTO':
			self.max_auto_scale = True
			#self.max_auto_scale = False
			#self.max_intensity = self.min_intensity + 60
		else:
			self.max_auto_scale = False
			self.max_intensity = float(intensity)
		self._clear_intensity()


	def get_fft_ave(self):
		return self.fft_ave


	def set_fft_ave(self, fft_ave):
		if fft_ave > 1:
			self.fft_ave = int(fft_ave)
		else:
			self.fft_ave = self.get_fft_ave

	def get_tune_rate(self):
		return self.tune_rate


	def set_tune_rate(self, tune_rate):
		self.tune_rate = float(tune_rate)


	def get_zoom_fac(self):
		return self.zoom_fac


	def set_zoom_fac(self, zoom_fac):
		self.zoom_fac = float(zoom_fac)


	def get_sig_strength(self):
		return float(self.sig_strength)


	def set_sig_strength(self, sig_strength):
		self.sig_strength = float(sig_strength)


	def get_filter(self):
		return self.filter


	def set_filter(self, filter): 
		self.filter = filter


	def get_kaiser_beta(self):
		return self.kaiser_beta


	def set_kaiser_beta(self, kaiser_beta):
		self.kaiser_beta = float(kaiser_beta)


	def get_freq_step(self):
		if self.zoom_fac < (self.sdr.sample_rate/1000000):
                        zoom = int(self.width*((self.sdr.sample_rate/1000000)/self.zoom_fac))
                else:
                        zoom = self.width
                        self.zoom_fac = self.get_sample_rate()		
		freq_step = self.sdr.sample_rate/(zoom+2)
		return freq_step


	def get_data(self):
		"""Get spectrogram data from the tuner.  Will return width number of
		values which are the intensities of each frequency bucket (i.e. FFT of
		radio samples).
		"""
		# Get width number of raw samples so the number of frequency bins is
		# the same as the display width.  Add two because there will be mean/DC
		# values in the results which are ignored. Increase by 1/self.zoom_fac if needed		
		

		if self.zoom_fac < (self.sdr.sample_rate/1000000):
			zoom = int(self.width*((self.sdr.sample_rate/1000000)/self.zoom_fac))
		else:
			zoom = self.width
			self.zoom_fac = self.get_sample_rate()

		if zoom < freqshow.SDR_SAMPLE_SIZE:		
			freqbins = self.sdr.read_samples(freqshow.SDR_SAMPLE_SIZE)[0:zoom+2]
		else:
			zoom = self.width
			self.zoom_fac = self.get_sample_rate()
			freqbins = self.sdr.read_samples(freqshow.SDR_SAMPLE_SIZE)[0:zoom+2]


		# Apply a window function to the sample to remove power in sample sidebands before the fft.
	
		if self.filter == 'kaiser':
			window = signal.kaiser(freqshow.SDR_SAMPLE_SIZE, self.kaiser_beta, False,)[0:zoom+2]  # for every bin there is a window the same exact size as the read samples.
		elif self.filter == 'boxcar':
			window = signal.boxcar(freqshow.SDR_SAMPLE_SIZE, False,)[0:zoom+2]
                elif self.filter == 'hann':
                        window = signal.hann(freqshow.SDR_SAMPLE_SIZE, False,)[0:zoom+2]	
                elif self.filter == 'hamming':
                        window = signal.hamming(freqshow.SDR_SAMPLE_SIZE, False,)[0:zoom+2]
                elif self.filter == 'blackman':
                        window = signal.blackman(freqshow.SDR_SAMPLE_SIZE, False,)[0:zoom+2]
                elif self.filter == 'blackmanharris':
                        window = signal.blackmanharris(freqshow.SDR_SAMPLE_SIZE, False,)[0:zoom+2]
                elif self.filter == 'bartlett':
                        window = signal.bartlett(freqshow.SDR_SAMPLE_SIZE, False,)[0:zoom+2]
                elif self.filter == 'barthann':
                        window = signal.barthann(freqshow.SDR_SAMPLE_SIZE, False,)[0:zoom+2]
                elif self.filter == 'nuttall':
                        window = signal.nuttall(freqshow.SDR_SAMPLE_SIZE, False,)[0:zoom+2]
		else:
			window = 1

		samples = freqbins * window

		# Run an FFT and take the absolute value to get frequency magnitudes.		
		freqs = np.absolute(fft(samples))

		# Ignore the mean/DC values at the ends.
		freqs = freqs[1:-1] 

                # Reverse the order of the freqs array if swaping I and Q
		if self.swap_iq == True:
                	freqs = freqs[::-1]

		# Shift FFT result positions to put center frequency in center.
		freqs = np.fft.fftshift(freqs)

               	# Truncate the freqs array to the width of the screen if neccesary.
                if freqs.size > self.width:

                	freq_step = self.get_freq_step()   # Get the frequency step in Hz between pixels.
                	shiftsweep = int(self.get_lo_offset()*1000000/freq_step) # LO offset in pixels.
                	extra_samples = int((freqs.size - self.width)/2)  # The excess samples either side of the display width in pixels.

                	if extra_samples > abs(shiftsweep): # check if there is room to shift the array by the LO offset.

                        	if self.get_swap_iq() == True:
                                	lextra = extra_samples + shiftsweep
                        	elif self.get_swap_iq() == False:
                                	lextra = extra_samples - shiftsweep
                	else:
                        	lextra = extra_samples

			rextra = freqs.size - (lextra + self.width)
			freqs = freqs[lextra:-rextra]

		# Convert to decibels.
		freqs = 20.0*np.log10(freqs)

		# Get signal strength of the center frequency.

#		for i in range ( 1, 11):
#			self.sig_strength = (self.get_sig_strength() + freqs[((zoom+2)/2)+i-5])
#		self.sig_strength = self.get_sig_strength()/10

		# Update model's min and max intensities when auto scaling each value.
		if self.min_auto_scale:
			min_intensity = np.min(freqs)
			self.min_intensity = min_intensity if self.min_intensity is None \
				else min(min_intensity, self.min_intensity)
		if self.max_auto_scale:
			max_intensity = np.max(freqs)
			self.max_intensity = max_intensity if self.max_intensity is None \
				else max(max_intensity, self.max_intensity)
		# Update intensity range (length between min and max intensity).
		self.range = self.max_intensity - self.min_intensity

		# Return frequency intensities.
		return freqs
