#!/usr/bin/env python

import gtk
from gi.repository import Gtk
from gi.repository import GObject
import math
import glob
import imp
import traceback

from views.components.input_panel import Input_Panel
from views.components.controller_panel import Controller_Panel
from views.components.menu_bar import Menu_Bar
from views.components.resize_box import ResizeBox
import simulator.sim_manager

from matplotlib.backends.backend_gtk3 import TimerGTK3
import settings


# Fix for a method that is not properly introspected
_child_get_property = Gtk.Container.child_get_property
def child_get_property(self, child, name):
    v = GObject.Value()
    v.init(int)
    _child_get_property(self, child, name, v)
    return v.get_int()
Gtk.Container.child_get_property = child_get_property


class MainFrame:
    def __init__(self, sim_manager, controller):
        self.sim_manager = sim_manager
        self.controller = controller

        self.vbox = gtk.VBox(False, 0)
        self.playing = False
        self.press = None
        self.resize = False
        self.resize_info = None

        self.resize_boxes = {}

        # create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_default_size(settings.VISUALIZER_WIDTH, 
                                     settings.VISUALIZER_HEIGHT)
        self.window.set_title("Nengo Visualizer")
        self.window.connect("delete_event", self.on_quit)

        self.input_panel = Input_Panel(self)
        self.controller_panel = Controller_Panel(self)
        self.menu_bar = Menu_Bar(self, controller)

        self.layout_event_box = gtk.EventBox()
        self.canvas_layout = gtk.Layout()
        self.layout_event_box.modify_bg(gtk.STATE_NORMAL, 
                                        gtk.gdk.color_parse("#ffffff"))
        self.layout_event_box.connect("button_release_event", 
                                      controller.on_layout_button_release)

        # Used to control framerate for redrawing graph components
        # rate at which we call sim.step()
        self.sim_rate = settings.SIMULATOR_DEFAULT_SIM_RATE 
        self.framerate = settings.SIMULATOR_FRAME_RATE
        self.next_gcomponent_redraw = 0

        # pretend new_timer is a static method
        self.timer = TimerGTK3(interval=settings.VISUALIZER_TIMER_INTERVAL)
        self.timer.add_callback(self.step)
        self.timer.single_shot = True

        self.vbox.pack_start(self.menu_bar, False, False, 0)
        self.vbox.pack_start(self.controller_panel, False, False, 0)

        self.layout_event_box.add(self.canvas_layout)

        self.vbox.pack_start(self.layout_event_box, True, True, 0)

        self.window.add(self.vbox)

        self.window.show_all()

        self.controller_panel.toggle_play(False)

    def on_quit(self, widget, event):
        self.controller.on_quit()
        gtk.main_quit()

    def hscale_change(self, range, scroll, value):
        if value < self.sim_manager.min_step or \
           value > self.sim_manager.last_sim_step:
            return
        self.sim_manager.current_step = value
        self.update_canvas()

    # Move some of this functionality to the controller
    def step(self):
        if (self.playing == True):
            self.sim_manager.step()

            self.controller_panel.update_slider(self.sim_manager.min_step, 
                                                self.sim_manager.last_sim_step,
                                                self.sim_manager.current_step, 
                                                self.sim_manager.dt)

            if (self.next_gcomponent_redraw == 0):
                self.update_canvas()
                self.next_gcomponent_redraw = self.sim_rate/self.framerate
            else:
                self.next_gcomponent_redraw -= 1

            self.timer.start(settings.VISUALIZER_TIMER_INTERVAL)

    def update_canvas(self):
        self.canvas_layout.queue_draw()

    #Controller code for controller_panel
    def format_slider_value(self, scale, value):
        return '%.3f' % (value * self.sim_manager.dt)

    def play_pause_button(self, widget):
        if (self.playing == True):
            self.timer.stop()
            self.playing = False
            self.controller_panel.toggle_play(self.playing)
            self.update_canvas()
        else:
            self.timer.start(1)
            self.playing = True
            self.controller_panel.toggle_play(self.playing)

    def reset_button(self, widget):
        self.timer.stop()
        self.playing = False
        self.controller_panel.toggle_play(False)

        self.controller_panel.hscale_adjustment.set_lower(0)
        self.controller_panel.hscale_adjustment.set_upper(0)
        self.controller_panel.update_slider(0, 0, 0, self.sim_manager.dt)
        self.sim_manager.reset()
        self.jump_to(widget, self.sim_manager.min_step)

    def jump_to_front(self, widget):
        self.jump_to(widget, self.sim_manager.min_step)

    def jump_to(self, widget, value):
        self.playing = True
        self.play_pause_button(widget)
        self.sim_manager.current_step = value
        self.controller_panel.set_slider(self.sim_manager.current_step)
        self.update_canvas()

    def jump_to_end(self, widget):
        self.jump_to(widget, self.sim_manager.last_sim_step)

    def on_button_release(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS:
            widget.popup(None, None, None, event.button, event.time)
            # Tell calling code that we have handled this event the buck
            # stops here.
            return True
        # Tell calling code that we have not handled this event pass it on.
        return False

    # Print a string when a menu item is selected
    def menuitem_response(self, widget, string):
        print "%s" % string

    def show_plot(self, plot, center=False, position=None, size=None):
        """
        center (boolean): center the plot, ignore position
        position (tuple): x, y coords to position the plot
        """
        resize_box = ResizeBox(plot, self.canvas_layout)
        self.canvas_layout.put(resize_box, 0, 0)
        self.resize_boxes[plot] = resize_box
        # Set position
        if (center):
            x = (self.window.get_allocated_width() - 
                 resize_box.get_width()) / 2
            y = (self.canvas_layout.get_allocated_height() - 
                 resize_box.get_height()) / 2
        elif position:
            x, y = position
        else:
            x = 0
            y = 0
        resize_box.set_position(x, y)
        # Set size
        if size:
            resize_box.set_size(*size)

        plot.apply_config()

    def remove_plot(self, plot):
        self.canvas_layout.remove(self.resize_boxes[plot])
        del self.resize_boxes[plot]

    def get_item_position(self, item):
        return (self.resize_boxes[item].pos_x, self.resize_boxes[item].pos_y)

    def get_item_size(self, item):
        return (self.resize_boxes[item].get_width(), 
                self.resize_boxes[item].get_height())

    def set_item_position(self, item, position):
        x, y = position
        self.resize_boxes[item].set_position(x, y)

    def set_item_size(self, item, size):
        w, h = size
        self.resize_boxes[item].set_size(w, h)

    def toggle_panel(self, widget, panel):
        if (widget.get_active()):
            panel.set_visible(True)
            self.control_panel.add(panel)
        else:
            panel.set_visible(False)
            self.control_panel.remove(panel)

