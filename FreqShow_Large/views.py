# FreqShow application views.
# These contain the majority of the application business logic.
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
import math
import sys

import numpy as np
import pygame

import freqshow
import ui


# Color and gradient interpolation functions used by waterfall spectrogram.
def lerp(x, x0, x1, y0, y1):
	"""Linear interpolation of value y given min and max y values (y0 and y1),
	min and max x values (x0 and x1), and x value.
	"""
	return y0 + (y1 - y0)*((x - x0)/(x1 - x0))

def rgb_lerp(x, x0, x1, c0, c1):
	"""Linear interpolation of RGB color tuple c0 and c1."""
	return (math.floor(lerp(x, x0, x1, float(c0[0]), float(c1[0]))),
			math.floor(lerp(x, x0, x1, float(c0[1]), float(c1[1]))),
			math.floor(lerp(x, x0, x1, float(c0[2]), float(c1[2]))))

def gradient_func(colors):
	"""Build a waterfall color function from a list of RGB color tuples.  The
	returned function will take a numeric value from 0 to 1 and return a color
	interpolated across the gradient of provided RGB colors.
	"""
	grad_width = 1.0 / (len(colors)-1.0)
	def _fun(value):
		if value <= 0.0:
			return colors[0]
		elif value >= 1.0:
			return colors[-1]
		else:
			pos = int(value / grad_width)
			c0 = colors[pos]
			c1 = colors[pos+1]
			x = (value % grad_width)/grad_width
			return rgb_lerp(x, 0.0, 1.0, c0, c1)
	return _fun

def clamp(x, x0, x1):
	"""Clamp a provided value to be between x0 and x1 (inclusive).  If value is
	outside the range it will be truncated to the min/max value which is closest.
	"""
	if x > x1:
		return x1
	elif x < x0:
		return x0
	else:
		return x


class ViewBase(object):
	"""Base class for simple UI view which represents all the elements drawn
	on the screen.  Subclasses should override the render, and click functions.
	"""

	def render(self, screen):
		pass

	def click(self, location):
		pass


class MessageDialog(ViewBase):
	"""Dialog which displays a message in the center of the screen with an OK
	and optional cancel button.
	"""

	def __init__(self, model, text, accept, cancel=None):
		self.accept = accept
		self.cancel = cancel
		self.buttons = ui.ButtonGrid(model.width, model.height, 4, 5)
		self.buttons.add(3, 4, 'OK', click=self.accept_click, 
			bg_color=freqshow.ACCEPT_BG)
		if cancel is not None:
			self.buttons.add(0, 4, 'CANCEL', click=self.cancel_click, 
				bg_color=freqshow.CANCEL_BG)
		self.label = ui.render_text(text, size=freqshow.NUM_FONT,
			fg=freqshow.BUTTON_FG, bg=freqshow.MAIN_BG)
		self.label_rect = ui.align(self.label.get_rect(),
			(0, 0, model.width, model.height))

	def render(self, screen):
		# Draw background, buttons, and text.
		screen.fill(freqshow.MAIN_BG)
		self.buttons.render(screen)
		screen.blit(self.label, self.label_rect)

	def click(self, location):
		self.buttons.click(location)

	def accept_click(self, button):
		self.accept()

	def cancel_click(self, button):
		self.cancel()


class NumberDialog(ViewBase):
	"""Dialog which asks the user to enter a numeric value."""

	def __init__(self, model, label_text, unit_text, initial='0', accept=None,
		cancel=None, has_auto=False, allow_negative=False):
		"""Create number dialog for provided model and with given label and unit
		text.  Can provide an optional initial value (default to 0), an accept
		callback function which is called when the user accepts the dialog (and
		the chosen value will be sent as a single parameter), a cancel callback
		which is called when the user cancels, and a has_auto boolean if an
		'AUTO' option should be given in addition to numbers.
		"""
		self.value = str(initial)
		self.unit_text = unit_text
		self.model = model
		self.accept = accept
		self.cancel = cancel
		# Initialize button grid.
		self.buttons = ui.ButtonGrid(model.width, model.height, 4, 5)
		self.buttons.add(0, 1, '1', font_size=freqshow.NUM_FONT, click=self.number_click)
		self.buttons.add(1, 1, '2', font_size=freqshow.NUM_FONT, click=self.number_click)
		self.buttons.add(2, 1, '3', font_size=freqshow.NUM_FONT, click=self.number_click)
		self.buttons.add(0, 2, '4', font_size=freqshow.NUM_FONT, click=self.number_click)
		self.buttons.add(1, 2, '5', font_size=freqshow.NUM_FONT, click=self.number_click)
		self.buttons.add(2, 2, '6', font_size=freqshow.NUM_FONT, click=self.number_click)
		self.buttons.add(0, 3, '7', font_size=freqshow.NUM_FONT, click=self.number_click)
		self.buttons.add(1, 3, '8', font_size=freqshow.NUM_FONT, click=self.number_click)
		self.buttons.add(2, 3, '9', font_size=freqshow.NUM_FONT, click=self.number_click)
		self.buttons.add(1, 4, '0', font_size=freqshow.NUM_FONT, click=self.number_click)
		self.buttons.add(2, 4, '.', font_size=freqshow.NUM_FONT, click=self.decimal_click)
		self.buttons.add(0, 4, 'DELETE', click=self.delete_click)
		if not allow_negative:
			# Render a clear button if only positive values are allowed.
			self.buttons.add(3, 1, 'CLEAR', click=self.clear_click)
		else:
			# Render a +/- toggle if negative values are allowed.
			self.buttons.add(3, 1, '+/-', click=self.posneg_click)
		self.buttons.add(3, 3, 'CANCEL', click=self.cancel_click,
			bg_color=freqshow.CANCEL_BG)
		self.buttons.add(3, 4, 'ACCEPT', click=self.accept_click,
			bg_color=freqshow.ACCEPT_BG) 
		if has_auto:
			self.buttons.add(3, 2, 'AUTO', click=self.auto_click)
		# Build label text for faster rendering.
		self.input_rect = (0, 0, self.model.width, self.buttons.row_size)
		self.label = ui.render_text(label_text, size=freqshow.MAIN_FONT, 
			fg=freqshow.INPUT_FG, bg=freqshow.INPUT_BG)
		self.label_pos = ui.align(self.label.get_rect(), self.input_rect,
			horizontal=ui.ALIGN_LEFT, hpad=10)


	def render(self, screen):
		# Clear view and draw background.
		screen.fill(freqshow.MAIN_BG)
		# Draw input background at top of screen.
		screen.fill(freqshow.INPUT_BG, self.input_rect)
		# Render label and value text.
		screen.blit(self.label, self.label_pos)
		value_label = ui.render_text('{0} {1}'.format(self.value, self.unit_text),
			size=freqshow.NUM_FONT, fg=freqshow.INPUT_FG, bg=freqshow.INPUT_BG)
		screen.blit(value_label, ui.align(value_label.get_rect(), self.input_rect,
			horizontal=ui.ALIGN_RIGHT, hpad=-10))
		# Render buttons.
		self.buttons.render(screen)

	def click(self, location):
		self.buttons.click(location)

	# Button click handlers follow below.
	def auto_click(self, button):
		self.value = 'AUTO'

	def clear_click(self, button):
		self.value = '0'

	def delete_click(self, button):
		if self.value == 'AUTO':
			# Ignore delete in auto gain mode.
			return
		elif len(self.value) > 1:
			# Delete last character.
			self.value = self.value[:-1]
		else:
			# Set value to 0 if only 1 character.
			self.value = '0'

	def cancel_click(self, button):
		if self.cancel is not None:
			self.cancel()

	def accept_click(self, button):
		if self.accept is not None:
			self.accept(self.value)

	def decimal_click(self, button):
		if self.value == 'AUTO':
			# If in auto gain, assume user wants numeric gain with decimal.
			self.value = '0.'
		elif self.value.find('.') == -1:
			# Only add decimal if none is present.
			self.value += '.'

	def number_click(self, button):
		if self.value == '0' or self.value == 'AUTO':
			# Replace value with number if no value or auto gain is set.
			self.value = button.text
		else:
			# Add number to end of value.
			self.value += button.text

	def posneg_click(self, button):
		if self.value == 'AUTO':
			# Do nothing if value is auto.
			return
		else:
			if self.value[0] == '-':
				# Swap negative to positive by removing leading minus.
				self.value = self.value[1:]
			else:
				# Swap positive to negative by adding leading minus.
				self.value = '-' + self.value



class FilterDialog(ViewBase):
        """Dialog which asks the user to enter a filter value."""

        def __init__(self, model, label_text, unit_text, initial='0', accept=None, cancel=None):
                """Create a dialog for provided model and with given label and unit
                text.  Can provide an optional initial value (default to True), an accept
                callback function which is called when the user accepts the dialog (and
                the chosen value will be sent as a single parameter), a cancel callback
                which is called when the user cancels.
                """
                self.value = str(initial)
                self.unit_text = unit_text
                self.model = model
                self.accept = accept
                self.cancel = cancel
                # Initialize button grid.
                self.buttons = ui.ButtonGrid(model.width, model.height, 4, 5)
                self.buttons.add(0, 1, 'boxcar', font_size=26,  click=self.boxcar_click)
                self.buttons.add(1, 1, 'hann', font_size=26, click=self.hann_click)
                self.buttons.add(2, 1, 'hamming', font_size=26, click=self.hamming_click)
                self.buttons.add(0, 2, 'blackman', font_size=26, click=self.blackman_click)
                self.buttons.add(1, 2, 'bharris', font_size=26, click=self.blackmanharris_click)
                self.buttons.add(2, 2, 'bartlett', font_size=26, click=self.bartlett_click)
                self.buttons.add(0, 3, 'barthann', font_size=26, click=self.barthann_click)
                self.buttons.add(1, 3, 'nuttall', font_size=26, click=self.nuttall_click)
                self.buttons.add(2, 3, 'kaiser', font_size=26, click=self.kaiser_click)
                self.buttons.add(3, 3, 'CANCEL', click=self.cancel_click,
                        bg_color=freqshow.CANCEL_BG)
                self.buttons.add(3, 4, 'ACCEPT', click=self.accept_click,
                        bg_color=freqshow.ACCEPT_BG)
                # Build label text for faster rendering.
                self.input_rect = (0, 0, self.model.width, self.buttons.row_size)
                self.label = ui.render_text(label_text, size=freqshow.MAIN_FONT,
                        fg=freqshow.INPUT_FG, bg=freqshow.INPUT_BG)
                self.label_pos = ui.align(self.label.get_rect(), self.input_rect,
                        horizontal=ui.ALIGN_LEFT, hpad=9)

        def render(self, screen):
                # Clear view and draw background.
                screen.fill(freqshow.MAIN_BG)
                # Draw input background at top of screen.
                screen.fill(freqshow.INPUT_BG, self.input_rect)
                # Render label and value text.
                screen.blit(self.label, self.label_pos)
                value_label = ui.render_text('{0} {1}'.format(self.value, self.unit_text),
                        size=freqshow.NUM_FONT, fg=freqshow.INPUT_FG, bg=freqshow.INPUT_BG)
                screen.blit(value_label, ui.align(value_label.get_rect(), self.input_rect,
                        horizontal=ui.ALIGN_RIGHT, hpad=-9))
                # Render buttons.
                self.buttons.render(screen)

        def click(self, location):
                self.buttons.click(location)

        # Button click handlers follow below.

        def boxcar_click(self, button):
                self.value = 'boxcar'

        def hann_click(self, button):
                self.value = 'hann'

        def hamming_click(self, button):
                self.value = 'hamming'

        def blackman_click(self, button):
                self.value = 'blackman'

        def blackmanharris_click(self, button):
                self.value = 'blackmanharris'

        def bartlett_click(self, button):
                self.value = 'bartlett'

        def barthann_click(self, button):
                self.value = 'barthann'

        def nuttall_click(self, button):
                self.value = 'nuttall'

        def kaiser_click(self, button):
                self.value = 'kaiser'

       	def cancel_click(self, button):
                if self.cancel is not None:
                        self.cancel()

        def accept_click(self, button):
                if self.accept is not None:
                        self.accept(self.value)




class BooleanDialog(ViewBase):
        """Dialog which asks the user to enter a boolean value."""

        def __init__(self, model, label_text, unit_text, initial='0', accept=None, cancel=None):
                """Create boolean dialog for provided model and with given label and unit
                text.  Can provide an optional initial value (default to True), an accept
                callback function which is called when the user accepts the dialog (and
                the chosen value will be sent as a single parameter), a cancel callback
                which is called when the user cancels.
                """
                self.value = str(initial)
		self.unit_text = unit_text
                self.model = model
                self.accept = accept
                self.cancel = cancel
                # Initialize button grid.
                self.buttons = ui.ButtonGrid(model.width, model.height, 4, 5)
                self.buttons.add(0, 1, 'False', font_size=freqshow.NUM_FONT, click=self.false_click)
                self.buttons.add(1, 1, 'True', font_size=freqshow.NUM_FONT, click=self.true_click)
                self.buttons.add(3, 3, 'CANCEL', click=self.cancel_click,
                        bg_color=freqshow.CANCEL_BG)
                self.buttons.add(3, 4, 'ACCEPT', click=self.accept_click,
                        bg_color=freqshow.ACCEPT_BG)
                # Build label text for faster rendering.
                self.input_rect = (0, 0, self.model.width, self.buttons.row_size)
                self.label = ui.render_text(label_text, size=freqshow.MAIN_FONT,
                        fg=freqshow.INPUT_FG, bg=freqshow.INPUT_BG)
                self.label_pos = ui.align(self.label.get_rect(), self.input_rect,
                        horizontal=ui.ALIGN_LEFT, hpad=2)

        def render(self, screen):
                # Clear view and draw background.
                screen.fill(freqshow.MAIN_BG)
                # Draw input background at top of screen.
                screen.fill(freqshow.INPUT_BG, self.input_rect)
                # Render label and value text.
                screen.blit(self.label, self.label_pos)
                value_label = ui.render_text('{0} {1}'.format(self.value, self.unit_text),
                        size=freqshow.NUM_FONT, fg=freqshow.INPUT_FG, bg=freqshow.INPUT_BG)
                screen.blit(value_label, ui.align(value_label.get_rect(), self.input_rect,
                        horizontal=ui.ALIGN_RIGHT, hpad=-2))
                # Render buttons.
                self.buttons.render(screen)


        def click(self, location):
                self.buttons.click(location)

        # Button click handlers follow below.

        def false_click(self, button):
                self.value = False

	def true_click(self, button):
		self.value = True


        def cancel_click(self, button):
                if self.cancel is not None:
                        self.cancel()

        def accept_click(self, button):
                if self.accept is not None:
                        self.accept(self.value)


class SettingsList(ViewBase):
	"""Setting list view. Allows user to modify some model configuration."""

	def __init__(self, model, controller):
		self.model      = model
		self.controller = controller
		# Create button labels with current model values.
		centerfreq_text = 'Center Freq: {0:0.6f} MHz'.format(model.get_center_freq())
		samplerate_text = 'Sample Rate: {0:0.3f} MHz'.format(model.get_sample_rate())
		gain_text       = 'Gain: {0} dB'.format(model.get_gain())
		min_text        = 'Min: {0} dB'.format(model.get_min_string())
		max_text        = 'Max: {0} dB'.format(model.get_max_string())
		fft_ave_text    = 'FFT ave: {0}'.format(model.get_fft_ave())
		tune_rate_text	= 'Tune Rate: {0:0.3f} MHz'.format(model.get_tune_rate())
		lo_offset_text = 'LO Offset: {0:0.2f} MHz'.format(model.get_lo_offset())
		zoom_fac_text = 'Zoom: {0:0.3f} MHz'.format(model.get_zoom_fac())
		freq_correction_text = 'Freq Corr: {0} ppm'.format(model.get_freq_correction()) 
		filter_text = '{0}'.format(model.get_filter())
		kaiser_beta_text = 'beta:{0:0.1f}'.format(model.get_kaiser_beta())
		swap_iq_text = 'Swap IQ: {0}'.format(model.get_swap_iq())
               	peak_text = 'Peak: {0}'.format(model.get_peak())

		# Create buttons.
		self.buttons = ui.ButtonGrid(model.width, model.height, 4, 6)
		self.buttons.add(0, 0, centerfreq_text, colspan=2, click=self.centerfreq_click)
		self.buttons.add(0, 1, samplerate_text, colspan=2, click=self.sample_click)
		self.buttons.add(0, 2, fft_ave_text,    colspan=1, click=self.fft_ave_click)
		self.buttons.add(2, 1, tune_rate_text,  colspan=2, click=self.tune_rate_click)
		self.buttons.add(2, 0, zoom_fac_text,   colspan=2, click=self.zoom_fac_click)
		self.buttons.add(0, 3, freq_correction_text, colspan=2, click=self.freq_correction_click)
		self.buttons.add(2, 4, gain_text,       colspan=1, click=self.gain_click)
		self.buttons.add(0, 4, min_text,        colspan=1, click=self.min_click)
		self.buttons.add(1, 4, max_text,        colspan=1, click=self.max_click)
		self.buttons.add(3, 5, 'BACK', 		colspan=1, click=self.controller.change_to_main)
		self.buttons.add(1, 2, lo_offset_text, colspan=2, click=self.lo_offset_click)		
		self.buttons.add(2, 3, filter_text, colspan=1, click=self.filter_click)
		if self.model.get_filter() == 'kaiser':
			self.buttons.add(3, 3, kaiser_beta_text, colspan=1, click=self.kaiser_beta_click)
		self.buttons.add(0, 5, swap_iq_text,    colspan=1, click=self.swap_iq_click)
                self.buttons.add(1, 5, peak_text,    colspan=1, click=self.peak_click)

	def render(self, screen):
		# Clear view and render buttons.
		screen.fill(freqshow.MAIN_BG)
		self.buttons.render(screen)

	def click(self, location):
		self.buttons.click(location)

	# Button click handlers follow below.


	def centerfreq_click(self, button):
		self.controller.number_dialog('FREQUENCY:', 'MHz',
			initial='{0:0.6f}'.format(self.model.get_center_freq()),
			accept=self.centerfreq_accept)

	def centerfreq_accept(self, value):
		self.model.set_center_freq(float(value))
		self.controller.waterfall.clear_waterfall()
		self.controller.change_to_settings()

	def sample_click(self, button):
		self.controller.number_dialog('SAMPLE RATE:', 'MHz',
			initial='{0:0.3f}'.format(self.model.get_sample_rate()),
			accept=self.sample_accept)

	def sample_accept(self, value):
		self.model.set_sample_rate(float(value))
		self.controller.waterfall.clear_waterfall()
		self.controller.change_to_settings()

	def fft_ave_click(self, button):
		self.controller.number_dialog('FFT AVE:', 'X',
			initial=self.model.get_fft_ave(),
			accept=self.fft_ave_accept)
			
	def fft_ave_accept(self, value):
		self.model.set_fft_ave(value)
		self.controller.change_to_settings()		

	def tune_rate_click(self, button):
		self.controller.number_dialog('TUNE RATE:', 'MHz',
			initial='{0:0.3f}'.format(self.model.get_tune_rate()),
			accept=self.tune_rate_accept)

	def tune_rate_accept(self, value):
                self.model.set_tune_rate(value)
                self.controller.change_to_settings()

	def lo_offset_click(self, button):
		self.controller.number_dialog('LO OFFSET:', 'MHz',
			initial='{0:0.2f}'.format(self.model.get_lo_offset()),
			accept=self.lo_offset_accept, allow_negative=True)

	def lo_offset_accept(self, value):
		self.model.set_lo_offset(float(value))
		self.controller.change_to_settings()


	def zoom_fac_click(self, button):
		self.controller.number_dialog('ZOOM in:', 'MHz',
			initial='{0:0.3f}'.format(self.model.get_zoom_fac()),
			accept=self.zoom_fac_accept)
	
	def zoom_fac_accept(self, value):
		self.model.set_zoom_fac(value)
		self.controller.change_to_settings()


	def freq_correction_click(self, button):
		self.controller.number_dialog('Frequency correction:', 'ppm',
			initial='{0}'.format(self.model.get_freq_correction()),
			accept=self.freq_correction_accept, allow_negative=True)

	def freq_correction_accept(self, value):
		self.model.set_freq_correction(int(value))
		self.controller.change_to_settings()
				
		
	def gain_click(self, button):
		self.controller.number_dialog('GAIN:', 'dB',
			initial=self.model.get_gain(), accept=self.gain_accept, 
			has_auto=True)

	def gain_accept(self, value):
		self.model.set_gain(value)
		self.controller.waterfall.clear_waterfall()
		self.controller.change_to_settings()

	def min_click(self, button):
		self.controller.number_dialog('MIN:', 'dB',
			initial=self.model.get_min_string(), accept=self.min_accept, 
			has_auto=True, allow_negative=True)

	def min_accept(self, value):
		self.model.set_min_intensity(value)  
		self.controller.waterfall.clear_waterfall()
		self.controller.change_to_settings()

	def max_click(self, button):
		self.controller.number_dialog('MAX:', 'dB',
			initial=self.model.get_max_string(), accept=self.max_accept, 
			has_auto=True, allow_negative=True)

	def max_accept(self, value):
		self.model.set_max_intensity(value)
		self.controller.waterfall.clear_waterfall()
		self.controller.change_to_settings()


        def filter_click(self, button):
                self.controller.filter_dialog('Windowing filter:', ' ',
                        initial=self.model.get_filter(),
                        accept=self.filter_accept)


        def filter_accept(self, value):
                self.model.set_filter(value)
                self.controller.change_to_settings()



	def kaiser_beta_click(self, button):
		self.controller.number_dialog('kaiser beta:', ' ',
                        initial='{0:0.1f}'.format(self.model.get_kaiser_beta()),
                        accept=self.kaiser_beta_accept)


	def kaiser_beta_accept(self, value):
		self.model.set_kaiser_beta(float(value))
		self.controller.change_to_settings()


	def swap_iq_click(self, button):
		self.controller.boolean_dialog('Swap I&Q', ' ',
			initial=self.model.get_swap_iq(),
			accept=self.swap_iq_accept)
      
	def swap_iq_accept(self, value):
		self.model.set_swap_iq(value)
		self.controller.change_to_settings()

        def peak_click(self, button):
                self.controller.boolean_dialog('Peak', ' ',
                        initial=self.model.get_peak(),
                        accept=self.peak_accept)

        def peak_accept(self, value):
                self.model.set_peak(value)
                self.controller.change_to_settings()

class SpectrogramBase(ViewBase):
	"""Base class for a spectrogram view."""

	def __init__(self, model, controller):
		self.model      = model
		self.controller = controller
		self.buttons = ui.ButtonGrid(model.width, model.height, 5, 5)
		self.buttons.add(0, 0, 'Set', click=self.controller.change_to_settings)
                self.buttons.add(1, 0, 'Dn', click=self.scale_dn, colspan=1)
		self.buttons.add(1, 4, '<', click=self.dn_center_freq, colspan=1)
		self.buttons.add(3, 4, '>', click=self.up_center_freq, colspan=1)
                self.buttons.add(3, 0, 'Up', click=self.scale_up, colspan=1)
		self.buttons.add(2, 0, 'PANADAPTER', click=self.controller.toggle_main, colspan=1)
		self.buttons.add(4, 0, 'Quit', click=self.quit_click,
			bg_color=freqshow.MAIN_BG)
		self.overlay_enabled = True

        def scale_up(self, button):
                if self.model.get_min_string() == 'AUTO' or self.model.get_max_string() == 'AUTO':
			return
		else:
			minv = float(self.model.get_min_string()) + 5
			maxv = float(self.model.get_max_string()) + 5
			self.model.set_min_intensity(minv)
			self.model.set_max_intensity(maxv)
			self.controller.waterfall.clear_waterfall()
			self.controller.change_to_main()

        def scale_dn(self, button):
		if self.model.get_min_string() == 'AUTO' or self.model.get_max_string() == 'AUTO':
			return
		else:
			minv = float(self.model.get_min_string()) - 5
                        maxv = float(self.model.get_max_string()) - 5
                        self.model.set_min_intensity(minv)
                        self.model.set_max_intensity(maxv)
			self.controller.waterfall.clear_waterfall()
                	self.controller.change_to_main()


	def up_center_freq(self, button):
		freq_mhz     = self.model.get_center_freq() + self.model.get_tune_rate()
		self.model.set_center_freq(freq_mhz)
		self.controller.change_to_main()

	def dn_center_freq(self, button):
		freq_mhz     = self.model.get_center_freq() - self.model.get_tune_rate()
		self.model.set_center_freq(freq_mhz)
		self.controller.change_to_main()

	def render_spectrogram(self, screen):
		"""Subclass should implement spectorgram rendering in the provided
		surface.
		"""
		raise NotImplementedError

	def render_hash(self, screen, x, size=5, padding=2):
		"""Draw a hash mark (triangle) on the bottom row at the specified x
		position.
		"""
		y = self.model.height - self.buttons.row_size + padding
		pygame.draw.lines(screen, freqshow.SYMBOL_FG, False, 
			[(x, y), (x-size, y+size), (x+size, y+size), (x, y), (x, y+2*size)])

	def render_inv_hash(self, screen, x, size=5, padding=2):
		"""Draw a hash mark (triangle) on the top row at the specified x	
		position.
		"""
		y = self.buttons.row_size + padding
		pygame.draw.lines(screen, freqshow.SYMBOL_FG, False,
			[(x, y), (x-size, y-size), (x+size, y-size), (x, y), (x, y-2*size)])

	def render(self, screen):
		# Clear screen.
		screen.fill(freqshow.MAIN_BG)
		if self.overlay_enabled:
			# Draw shrunken spectrogram with overlaid buttons and axes values.
			spect_rect = (0, self.buttons.row_size, self.model.width,
				self.model.height-2*self.buttons.row_size)
			self.render_spectrogram(screen.subsurface(spect_rect))

			# Draw hash marks.
			self.render_hash(screen, 0)
			self.render_hash(screen, self.model.width/2)
			self.render_hash(screen, self.model.width-1)	

			# Draw frequencies in bottom row.
			bottom_row  = (0, self.model.height-self.buttons.row_size,
				self.model.width, self.buttons.row_size)

#			freq        = float(self.model.get_lo_freq()) - float(self.model.get_lo_offset())
			freq 	    = self.model.get_center_freq()
			bandwidth   = self.model.get_zoom_fac()
			sig         = (self.model.get_sig_strength()/6)		
			offset      = self.model.get_lo_offset()
			beta        = self.model.get_kaiser_beta()
		
			# Render minimum frequency on left.
			label = ui.render_text('- {0:0.4f} Mhz'.format(bandwidth/2.0),
				size=freqshow.MAIN_FONT, bg=freqshow.MAIN_BG)
			screen.blit(label, ui.align(label.get_rect(), bottom_row,
				horizontal=ui.ALIGN_LEFT))

			# Render center frequency in center.
			label = ui.render_text('{0:0.6f}'.format(freq),
				size=freqshow.MAIN_FONT, bg=freqshow.MAIN_BG)
			screen.blit(label, ui.align(label.get_rect(), bottom_row,
				horizontal=ui.ALIGN_CENTER))

			# Render maximum frequency on right.
			label = ui.render_text('+ {0:0.4f} Mhz'.format(bandwidth/2.0),
				size=freqshow.MAIN_FONT, bg=freqshow.MAIN_BG)
			screen.blit(label, ui.align(label.get_rect(), bottom_row,
				horizontal=ui.ALIGN_RIGHT))

			# Render min intensity in bottom left.
			label = ui.render_text('{0:0.0f} dB'.format(self.model.min_intensity),
				size=freqshow.MAIN_FONT, bg=freqshow.GRID_BG)
			screen.blit(label, ui.align(label.get_rect(), spect_rect,
				horizontal=ui.ALIGN_LEFT, vertical=ui.ALIGN_BOTTOM))

			# Render max intensity in top left.
			label = ui.render_text('{0:0.0f} dB'.format(self.model.max_intensity),
				size=freqshow.MAIN_FONT, bg=freqshow.GRID_BG)
			screen.blit(label, ui.align(label.get_rect(), spect_rect,
				horizontal=ui.ALIGN_LEFT, vertical=ui.ALIGN_TOP))

			# Render FFT average in bottom right.
			if self.model.get_peak() == True:
				label = ui.render_text('fft pks = {0}'.format(self.model.fft_ave),
					size=freqshow.MAIN_FONT, bg=freqshow.GRID_BG)
                                screen.blit(label, ui.align(label.get_rect(), spect_rect,
                                        horizontal=ui.ALIGN_RIGHT, vertical=ui.ALIGN_BOTTOM))
			elif self.model.get_peak() == False:
                                label = ui.render_text('fft ave = {0}'.format(self.model.fft_ave),
                                        size=freqshow.MAIN_FONT, bg=freqshow.GRID_BG)
				screen.blit(label, ui.align(label.get_rect(), spect_rect,
					horizontal=ui.ALIGN_RIGHT, vertical=ui.ALIGN_BOTTOM))

			# Render Grid scale factor in upper right.
			label = ui.render_text('scale = {0:0.1f} dB' .format((self.model.max_intensity-self.model.min_intensity)/10),
				size=freqshow.MAIN_FONT, bg=freqshow.GRID_BG)
			screen.blit(label, ui.align(label.get_rect(), spect_rect,
				horizontal=ui.ALIGN_RIGHT, vertical=ui.ALIGN_TOP)) 

			# Render Signal plus to Noise of Ceneter Frequency in center top.
#			label = ui.render_text('S units = {0:0.1f}' .format(sig),
#				size=freqshow.MAIN_FONT, bg=freqshow.GRID_BG)
#			screen.blit(label, ui.align(label.get_rect(), spect_rect,
#				horizontal=ui.ALIGN_CENTER, vertical=ui.ALIGN_TOP))

                        # Render windowing filter setting in center top.
			if self.model.filter == 'kaiser':
                       		label = ui.render_text('Kaiser beta = {0:0.1f}' .format(beta),
                               		size=freqshow.MAIN_FONT, bg=freqshow.GRID_BG)
                       		screen.blit(label, ui.align(label.get_rect(), spect_rect,
                               		horizontal=ui.ALIGN_CENTER, vertical=ui.ALIGN_TOP))
			else:
				label = ui.render_text('{0}' .format(self.model.filter),
                                        size=freqshow.MAIN_FONT, bg=freqshow.GRID_BG)
                                screen.blit(label, ui.align(label.get_rect(), spect_rect,
                                        horizontal=ui.ALIGN_CENTER, vertical=ui.ALIGN_TOP))



			# Draw the buttons.
			self.buttons.render(screen)
		else:
			# Draw fullscreen spectrogram.
			self.render_spectrogram(screen)

	def click(self, location):
		mx, my = location
		if my > self.buttons.row_size and my < 4*self.buttons.row_size:
			# Handle click on spectrogram.
			self.overlay_enabled = not self.overlay_enabled
		else:
			# Handle click on buttons.
			self.buttons.click(location)

	def quit_click(self, button):
		self.controller.message_dialog('QUIT: Are you sure?',
			accept=self.quit_accept)

	def quit_accept(self):
		sys.exit(0)


class WaterfallSpectrogram(SpectrogramBase):
	"""Scrolling waterfall plot of spectrogram data."""

	def __init__(self, model, controller):
		super(WaterfallSpectrogram, self).__init__(model, controller)
		self.color_func = gradient_func(freqshow.WATERFALL_GRAD)
		self.waterfall = pygame.Surface((model.width, model.height))

	def clear_waterfall(self):
		self.waterfall.fill(freqshow.MAIN_BG)

	def render_spectrogram(self, screen):
		# Grab spectrogram data.
		freqs = self.model.get_data()
		# Scroll up the waterfall display.
		self.waterfall.scroll(0, -1)
		# Scale the FFT values to the range 0 to 1.
		freqs = (freqs-self.model.min_intensity)/self.model.range
		# Convert scaled values to pixels drawn at the bottom of the display.
		x, y, width, height = screen.get_rect()
		wx, wy, wwidth, wheight = self.waterfall.get_rect()
		offset = wheight - height
		# Draw FFT values mapped through the gradient function to a color.
		self.waterfall.lock()

		for i in range(width):
			power = clamp(freqs[i], 0.0, 1.0)
			self.waterfall.set_at((i, wheight-1), self.color_func(power))
		self.waterfall.unlock()
		screen.blit(self.waterfall, (0, 0), area=(0, offset, width, height))
		
class InstantSpectrogram(SpectrogramBase):
	"""Instantaneous point in time line plot of the spectrogram."""

	def __init__(self, model, controller):	
                super(InstantSpectrogram, self).__init__(model, controller)
                self.checkfirst = self.model.fft_ave +1
                self.freqsfirst = self.model.get_data()
                self.freqsinit = np.tile(self.freqsfirst,(self.checkfirst,1))
               	self.freqgrabs = self.freqsinit.copy()
		self.color_func = gradient_func(freqshow.WATERFALL_GRAD)

	def render_spectrogram(self, screen):

		# Grab fft data and plot it.
		freqslast = self.model.get_data()		

		if (self.freqsfirst.size != freqslast.size) or (self.checkfirst != (self.model.fft_ave+1)): 
                        self.checkfirst = self.model.fft_ave +1
	                self.freqsfirst = self.model.get_data()
                	self.freqsinit = np.tile(self.freqsfirst,(self.checkfirst,1))
                	self.freqgrabs = self.freqsinit.copy()

 

		for i in range(1,self.model.fft_ave+1):
			np.copyto(self.freqgrabs[i-1],self.freqgrabs[i])		
		np.copyto(self.freqgrabs[self.model.fft_ave],freqslast)


		if self.model.get_peak() == True:
			freqs = np.max(self.freqgrabs, axis=0)
		elif self.model.get_peak() == False:
			freqs = np.average(self.freqgrabs, axis=0)


		# Scale frequency values to fit on the screen based on the min and max intensity values.
		x, y, width, height = screen.get_rect()
		freqs = height-np.floor(((freqs-self.model.min_intensity)/self.model.range)*height)

		# Render frequency graph.
		screen.fill(freqshow.GRID_BG)
		# Draw grid lines for spectrum background
		pygame.draw.line(screen, freqshow.GRID_LINE, (0, height/2), (width, height/2)) 
		pygame.draw.line(screen, freqshow.CENTER_LINE, (width/2, 0), (width/2, height))
		pygame.draw.line(screen, freqshow.GRID_LINE, (width/10, 0), (width/10, height))
		pygame.draw.line(screen, freqshow.GRID_LINE, (2*width/10, 0), (2*width/10, height))
		pygame.draw.line(screen, freqshow.GRID_LINE, (3*width/10, 0), (3*width/10, height))
		pygame.draw.line(screen, freqshow.GRID_LINE, (4*width/10, 0), (4*width/10, height))
		pygame.draw.line(screen, freqshow.GRID_LINE, (6*width/10, 0), (6*width/10, height))
		pygame.draw.line(screen, freqshow.GRID_LINE, (7*width/10, 0), (7*width/10, height))
		pygame.draw.line(screen, freqshow.GRID_LINE, (8*width/10, 0), (8*width/10, height))
		pygame.draw.line(screen, freqshow.GRID_LINE, (9*width/10, 0), (9*width/10, height))
		pygame.draw.line(screen, freqshow.GRID_LINE, (0, height/10), (width, height/10))
		pygame.draw.line(screen, freqshow.GRID_LINE, (0, 2*height/10), (width, 2*height/10))
		pygame.draw.line(screen, freqshow.GRID_LINE, (0, 3*height/10), (width, 3*height/10))
		pygame.draw.line(screen, freqshow.GRID_LINE, (0, 4*height/10), (width, 4*height/10))
		pygame.draw.line(screen, freqshow.GRID_LINE, (0, 6*height/10), (width, 6*height/10))
		pygame.draw.line(screen, freqshow.GRID_LINE, (0, 7*height/10), (width, 7*height/10))
		pygame.draw.line(screen, freqshow.GRID_LINE, (0, 8*height/10), (width, 8*height/10))
		pygame.draw.line(screen, freqshow.GRID_LINE, (0, 9*height/10), (width, 9*height/10))
		pygame.draw.line(screen, freqshow.GRID_LINE, (0, 0), (0, height-1))
		pygame.draw.line(screen, freqshow.GRID_LINE, (width-1, 0), (width-1, height-1))
		pygame.draw.line(screen, freqshow.GRID_LINE, (0, 0), (width-1, 0))
		pygame.draw.line(screen, freqshow.GRID_LINE, (0, height-1), (width-1, height-1))
		# Draw 0 DB reference line across screen.
		pygame.draw.line(screen, freqshow.CENTER_LINE, (0, (abs(self.model.max_intensity)/(self.model.max_intensity-self.model.min_intensity)*height)), (width-1, (abs(self.model.max_intensity)/(self.model.max_intensity-self.model.min_intensity)*height)))

		# Draw line segments to join each FFT result bin.
		ylast = freqs[0]		
#		freqs1 = freqs/height

		for i in range(1, width):
			y=freqs[i-1]
			#power = 1-freqs1[i]
			#pygame.draw.line(screen, self.color_func(power), (i-1, ylast), (i, y))
			#pygame.draw.line(screen, self.color_func(power), (i,y+1),(i,y+2))
			pygame.draw.line(screen, freqshow.INPUT_FG, (i-1, ylast), (i, y))
			pygame.draw.line(screen, freqshow.LINE_SHADOW, (i,y+3),(i,height))
	                ylast = y
	                       		
		# End of plot
