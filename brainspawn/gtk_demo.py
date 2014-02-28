#!/usr/bin/env python
import os
from sample_networks.spa_sequence.spa_sequence import net, pThal

import pygtk
pygtk.require('2.0')
import gtk
import cairo
import math

import view.components.spectrogram as spectrogram
from view.components.network_view import Network_View
#import view.components.input_panel as Input_Panel
from view.components.input_panel import Input_Panel
from view.components.controller_panel import Controller_Panel
from view.components.menu_bar import Menu_Bar
import simulator
import simulator.watchers
from old_plots.xy_plot import XY_Plot
from old_plots.voltage_grid import Voltage_Grid_Plot

from matplotlib.backends.backend_gtkcairo import FigureCanvasGTKCairo as FigureCanvas

class MainFrame:
    def __init__(self):

        self.vbox = gtk.VBox(False, 0)
        self.playing = False
        self.press = None
        self.resize = False
        self.resize_info = None

        self.sim = simulator.Simulator(net, net.dt)
        self.sim.add_watcher(simulator.watchers.LFPSpectrogramWatcher())
        self.sim.add_watcher(simulator.watchers.XYWatcher())
        self.sim.add_watcher(simulator.watchers.Voltage_Grid_Watcher())
        self.sim.watcher_manager.add_object("pThal", pThal)
        self.spectrogram = None

        self.all_plots = []
        self.all_canvas = []

        net.run(0.001) #run for one timestep
        self.sim.tick()
        self.sim.tick()

        for name, type, data in [("pThal", "LFP Spectrogram", None)]:
            if name in self.sim.watcher_manager.objects.keys():
                for (t, view_class, args) in self.sim.watcher_manager.list_watcher_views(name):
                    if t == type:
                        component = view_class(self.sim, name, **args)
                        # we know we only have the spectrogram in our example
                        self.spectrogram = component
                    elif (t == "XY"):
                        self.xy_plot = view_class(self.sim, name, **args)
                    elif (t == "Voltage Grid"):
                        self.voltage_grid = view_class(self.sim, name, **args)

        self.network_view = Network_View(self.sim)

        #TODO(amtinits): this should go in a super-class for all plots
        def button_press(widget, event, canvas):
            if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
                export_pdf_item = gtk.MenuItem("Export to PDF")
                export_pdf_item.connect("activate", self.on_export_pdf, canvas)
                export_pdf_item.show()
                context_menu = gtk.Menu()
                context_menu.append(export_pdf_item)
                context_menu.popup(None, None, None, event.button, event.time)
                return True
            return False

        self.spec_canvas = FigureCanvas(self.spectrogram.get_figure())
        self.spec_canvas.connect("event", button_press, self.spec_canvas)
        self.all_plots.append(self.spectrogram)
        self.all_canvas.append(self.spec_canvas)

        self.xy_canvas = FigureCanvas(self.xy_plot.get_figure())
        self.xy_canvas.connect("event", button_press, self.xy_canvas)
        self.all_plots.append(self.xy_plot)
        self.all_canvas.append(self.xy_canvas)

        self.vg_canvas = FigureCanvas(self.voltage_grid.get_figure())
        self.vg_canvas.connect("event", button_press, self.vg_canvas)
        self.all_plots.append(self.voltage_grid)
        self.all_canvas.append(self.vg_canvas)

        self.network_canvas = FigureCanvas(self.network_view.get_figure())
        self.network_canvas.connect("event", button_press, self.network_canvas)
        self.all_plots.append(self.network_view)
        self.all_canvas.append(self.network_canvas)

        map(lambda x:x.mpl_connect('figure_enter_event', self.enter_figure), self.all_canvas)
        map(lambda x:x.mpl_connect('figure_leave_event', self.leave_figure), self.all_canvas)
        map(lambda x:x.mpl_connect('button_press_event', self.mouse_on_press), self.all_canvas)
        map(lambda x:x.mpl_connect('button_release_event', self.mouse_on_release), self.all_canvas)
        map(lambda x:x.mpl_connect('motion_notify_event', self.mouse_on_motion), self.all_canvas)

        # create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_size_request(200, 100)
        self.window.set_title("Nengo Python Visualizer")
        self.window.connect("delete_event", lambda w,e: gtk.main_quit())

        self.input_panel = Input_Panel(self)
        self.controller_panel = Controller_Panel(self)
        self.menu_bar = Menu_Bar(self)

        self.canvas_layout = gtk.Layout(None, None)
        self.canvas_layout.set_size(600, 600)
        self.canvas_layout.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#ffffff"))

        figure = self.spectrogram.get_figure()

        # Used to control framerate for redrawing graph components
        self.sim_rate = 6 # rate at which we call sim.tick()
        self.framerate = 2
        self.next_gcomponent_redraw = 0

        self.canvas = FigureCanvas(figure)  # a gtk.DrawingArea
        self.timer = self.canvas.new_timer(interval=1000/self.sim_rate)
        self.timer.add_callback(self.tick)

        self.vbox.pack_start(self.menu_bar, False, False, 0)
        self.vbox.pack_start(self.controller_panel, False, False, 0)
        self.vbox.pack_start(self.canvas_layout, True, True, 0)
        self.window.add(self.vbox)

        self.menu_bar.show()
        self.controller_panel.show()
        self.spec_canvas.show()
        self.canvas_layout.show()
        self.vbox.show()

        self.window.set_size_request(800, 600)
        self.window.show()
        self.window.show_all()

        self.menu_bar.spectrogram_menu_item.set_active(True)

    def toggle_resize(self, widget):
        if (widget.get_active()):
            self.resize = True
        else:
            self.resize = False

    def mouse_on_press(self, event):
        canvas = event.canvas
        x0 = self.canvas_layout.child_get_property(canvas, "x")
        y0 = self.canvas_layout.child_get_property(canvas, "y")
        widget_x, widget_y = self.canvas_layout.get_pointer()
        self.press = x0, y0, widget_x, widget_y

    def mouse_on_motion(self, event):
        if self.press is None: return

        x0, y0, xpress, ypress = self.press
        owidth, oheight = event.canvas.get_width_height()

        canvas_layout_x, canvas_layout_y = self.canvas_layout.get_pointer()

        if (self.resize):
            if (self.resize_info == None):
                self.resize_info = xpress, ypress
            old_x, old_y = self.resize_info
            old_y = oheight - old_y
            o_mag = self.magnitude(old_x, old_y)

            new_mag = self.magnitude(canvas_layout_x, canvas_layout_y)
            self.resize_info = canvas_layout_x, canvas_layout_y
            scale = new_mag / o_mag
            scale = scale * scale
            new_width = int(owidth * scale)
            new_height = int(oheight * scale)
            event.canvas.set_size_request(new_width, new_height)
        else:
            # calc dx = currx - pressx
            widget_x, widget_y = self.canvas_layout.get_pointer()
            self.press = x0, y0, canvas_layout_x, canvas_layout_y
            dx = canvas_layout_x - xpress
            dy = canvas_layout_y - ypress
            new_x = int(round(x0 + dx))
            new_y = int(round(y0 + dy))
            self.canvas_layout.move(event.canvas, new_x, new_y)
            self.press = new_x, new_y, canvas_layout_x, canvas_layout_y

    def magnitude(self, x, y):
        sq1 = x * x
        sq2 = y * y
        return math.sqrt(sq1 + sq2)

    def mouse_on_release(self, event):
        self.press = None
        event.canvas.draw()

    def leave_figure(self, event):
        event.canvas.figure.patch.set_facecolor('white')
        event.canvas.draw()

    def enter_figure(self, event):
        event.canvas.figure.patch.set_facecolor('grey')
        event.canvas.draw()

    def hscale_change(self, range, scroll, value):
        self.sim.current_tick = value
        self.update_canvas()

    def tick(self):
        self.sim.tick()

        self.controller_panel.update_slider(self.sim.min_tick, self.sim.max_tick,
                                            self.sim.current_tick, self.sim.dt)

        if (self.next_gcomponent_redraw == 0):
            self.update_canvas()
            self.next_gcomponent_redraw = self.sim_rate/self.framerate
        else:
            self.next_gcomponent_redraw -= 1


    def update_canvas(self):

        if (self.xy_canvas.get_visible()):
            self.xy_plot.tick()
            self.xy_canvas.draw()
        if (self.vg_canvas.get_visible()):
            self.voltage_grid.tick()
            self.vg_canvas.draw()
        #self.i=(self.i+1) % 25
        if (self.spec_canvas.get_visible()):
            self.spectrogram.tick()
            self.spec_canvas.draw()
        if (self.network_canvas.get_visible()):
            self.network_view.tick()
            self.spec_canvas.draw()

    #Controller code for controller_panel
    def format_slider_value(self, scale, value):
        return str(value * self.sim.dt)

    def play_pause_button(self, widget):
        if (self.playing == True):
            self.timer.stop()
            self.playing = False
            self.controller_panel.toggle_play(self.playing)
        else:
            self.timer.start()
            self.playing = True
            self.controller_panel.toggle_play(self.playing)

    def reset_button(self, widget):
        self.timer.stop()
        self.playing = False
        self.controller_panel.toggle_play(self.playing)
        self.sim.reset()
        self.jump_to(widget, self.sim.min_tick)
        self.clear_all_graphs()

    def jump_to_front(self, widget):
        self.jump_to(widget, self.sim.min_tick)

    def jump_to(self, widget, value):
        self.playing = True
        self.play_pause_button(widget)
        self.sim.current_tick = value
        self.controller_panel.set_slider(self.sim.current_tick)
        self.update_canvas()

    def jump_to_end(self, widget):
        self.jump_to(widget, self.sim.max_tick)

    def button_press(self, widget, event):
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

    def toggle_plot(self, widget, canvas):
        if (widget.get_active()):
            canvas.set_visible(True)
            canvas.set_size_request(300, 300)
            canvas.show()
            self.canvas_layout.put(canvas, 0, 0)
        else:
            canvas.set_visible(False)
            self.canvas_layout.remove(canvas)

    def toggle_panel(self, widget, panel):
        if (widget.get_active()):
            panel.set_visible(True)
            self.control_panel.add(panel)
        else:
            panel.set_visible(False)
            self.control_panel.remove(panel)

    def clear_all_graphs(self):
        map(lambda x:x.clear(), self.all_plots)

    def repaint_all_canvas(self):
        map(lambda x:x.draw(), self.all_canvas)


    def on_export_pdf(self, widget, canvas=None):
        filename = self.file_browse(gtk.FILE_CHOOSER_ACTION_SAVE, "screenshot.pdf")
        if not filename:
            return
        with open(filename, "wb") as f:
            if canvas:
                canvas.print_pdf(f)
            else:
                cr = cairo.Context(cairo.PDFSurface(f, *self.window.get_size()))
                cr.set_source_surface(self.window.window.cairo_create().get_target())
                cr.set_operator(cairo.OPERATOR_SOURCE)
                cr.paint()
                cr.show_page()
                cr.get_target().finish()

    def file_browse(self, action, name="", ext="", ext_name=""):
        if (action == gtk.FILE_CHOOSER_ACTION_OPEN):
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        else:
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        dialog = gtk.FileChooserDialog(title="Select File", action=action, buttons=buttons)
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_folder(os.getcwd())
        dialog.set_current_name(name)

        if ext:
            filt = gtk.FileFilter()
            filt.set_name(ext_name if ext_name else ext)
            filt.add_pattern("*." + ext)
            dialog.add_filter(filt)

        filt = gtk.FileFilter()
        filt.set_name("All files")
        filt.add_pattern("*")
        dialog.add_filter(filt)

        result = ""
        if dialog.run() == gtk.RESPONSE_OK:
            result = dialog.get_filename()
        dialog.destroy()
        return result


if __name__ == "__main__":
    MainFrame()
    gtk.main()
