#!/usr/bin/env python
import os
import subprocess
import tempfile
from spa_sequence.spa_sequence import net, pThal

import pygtk
pygtk.require('2.0')
import gtk
import gobject

import view.components.spectrogram as spectrogram
#import view.components.input_panel as Input_Panel
from view.components.input_panel import Input_Panel
from view.components.controller_panel import Controller_Panel
import simulator
import simulator.watchers
from old_plots.xy_plot import XY_Plot
from old_plots.voltage_grid import Voltage_Grid_Plot

from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas

class MainFrame:
    def __init__(self):
        
        
        self.vbox = gtk.VBox(False, 0)
        self.playing = False

        self.sim = simulator.Simulator(net, net.dt)
        self.sim.add_watcher(simulator.watchers.LFPSpectrogramWatcher())
        self.sim.watcher_manager.add_object("pThal", pThal)
        self.spectrogram = None

        net.run(0.001) #run for one timestep

        for name, type, data in [("pThal", "LFP Spectrogram", None)]:
            if name in self.sim.watcher_manager.objects.keys():
                for (t, view_class, args) in self.sim.watcher_manager.list_watcher_views(name):
                    if t == type:
                        component = view_class(self.sim, name, **args)
                        # we know we only have the spectrogram in our example
                        self.spectrogram = component

        self.spec_canvas = FigureCanvas(self.spectrogram.get_figure())

        self.xy_plot = XY_Plot()
        self.xy_canvas = FigureCanvas(self.xy_plot.get_figure())
        self.i=0

        self.voltage_grid = Voltage_Grid_Plot()
        self.vg_canvas = FigureCanvas(self.voltage_grid.get_figure())

        # create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_size_request(200, 100)
        self.window.set_title("Nengo Python Visualizer")
        self.window.connect("delete_event", lambda w,e: gtk.main_quit())

        file_menu = gtk.MenuItem("File")
        file_submenu = gtk.Menu()
        file_menu.set_submenu(file_submenu)

        export_pdf_menu_item = gtk.MenuItem("Export to PDF")
        export_pdf_menu_item.connect('activate', self.on_export_pdf)
        export_pdf_menu_item.show()
        file_submenu.append(export_pdf_menu_item)

        file_menu.show()

        tools_menu = gtk.MenuItem("Tools")
        tools_submenu = gtk.Menu()
        tools_menu.set_submenu(tools_submenu)
        
        self.input_panel = Input_Panel()
        
        input_panel_menu_item = gtk.CheckMenuItem("Input Panel")
        input_panel_menu_item.connect("activate", self.toggle_panel, self.input_panel)
        input_panel_menu_item.show()
        tools_submenu.append(input_panel_menu_item)
        
        tools_menu.show()

        view_menu = gtk.MenuItem("View")
        view_submenu = gtk.Menu()
        view_menu.set_submenu(view_submenu)

        spectrogram_menu_item = gtk.CheckMenuItem("Spectrogram")
        spectrogram_menu_item.connect("activate", self.toggle_plot, self.spec_canvas)
        #spectrogram_menu_item.set_active(True)
        spectrogram_menu_item.show()
        view_submenu.append(spectrogram_menu_item)

        xy_plot_menu_item = gtk.CheckMenuItem("XY plot")
        xy_plot_menu_item.connect("activate", self.toggle_plot, self.xy_canvas)
        xy_plot_menu_item.show()
        view_submenu.append(xy_plot_menu_item)

        voltage_grid_menu_item = gtk.CheckMenuItem("Voltage Grid")
        voltage_grid_menu_item.connect("activate", self.toggle_plot, self.vg_canvas)
        voltage_grid_menu_item.show()
        view_submenu.append(voltage_grid_menu_item)

        view_menu.show()

        help_menu = gtk.MenuItem("Help")
        help_menu.show()

        #self.window.add(self.vbox)
        self.vbox.show()
        
        self.control_panel = gtk.HBox(False, 0)
        self.control_panel.show()
        
        self.hbox = gtk.HBox(False, 0)
        self.window.add(self.hbox)
        self.hbox.add(self.vbox)
        self.hbox.add(self.control_panel)
        self.hbox.show()

        menu_bar = gtk.MenuBar()
        menu_bar.show()
        menu_bar.set_size_request(300, 30)

        menu_bar.append (file_menu)
        menu_bar.append (tools_menu)
        menu_bar.append (view_menu)
        menu_bar.append (help_menu)
        self.vbox.pack_start(menu_bar, False, False, 2)

        frame = gtk.Frame(label="Spectrogram")
        frame.set_size_request(300, 300)

        figure = self.spectrogram.get_figure()

        self.canvas = FigureCanvas(figure)  # a gtk.DrawingArea
        self.timer = self.canvas.new_timer(interval=200)
        self.timer.add_callback(self.tick)
        self.spec_canvas.show()

        self.controller_panel = Controller_Panel(self)

        self.vbox.pack_start(self.controller_panel, False, False, 0)
#         controller_hbox.set_size_request(300, 50)
        self.controller_panel.show()

        self.window.set_size_request(500, 500)
        self.window.show()
        
        spectrogram_menu_item.set_active(True)

    def hscale_change(self, widget):
        self.sim.current_tick = (self.hscale_adjustment.get_value())
        self.update_canvas()

    def tick(self):
        self.sim.tick()

        self.controller_panel.hscale_adjustment.set_upper(self.sim.max_tick)
        self.controller_panel.hscale_adjustment.set_lower(self.sim.min_tick)
        #self.hscale_adjustment.set_value(self.sim.current_tick) # well, we'll need to find a way to keep this updated at some point

        self.update_canvas()

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


    def play_pause_button(self, widget):
        if (self.playing == True):
            self.timer.stop()
            self.playing = False
        else:
            self.timer.start()
            self.playing = True

    def stop_button(self, widget):
        self.timer.stop()
        self.playing = False

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
            self.vbox.add(canvas)
        else:
            canvas.set_visible(False)
            self.vbox.remove(canvas)
            
    def toggle_panel(self, widget, panel):
        if (widget.get_active()):
            panel.set_visible(True)
            self.control_panel.add(panel)
        else:
            panel.set_visible(False)
            self.control_panel.remove(panel)

    def on_export_pdf(self, widget):
        filename = self.file_browse(gtk.FILE_CHOOSER_ACTION_SAVE,
                                    "screenshot.pdf")
        if filename:
            gobject.timeout_add(1000, self._capture_window, filename)

    def _capture_window(self, filename):
            width, height = self.window.get_size()
            pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8,
                                    width, height)
            img = pixbuf.get_from_drawable(self.window.window,
                                           self.window.get_colormap(),
                                           0, 0, 0, 0, width, height)

            with tempfile.NamedTemporaryFile(suffix=".png") as temp:
                img.save(temp.name, "png")
                print "temp: " + str(temp.name)
                print "filename: " + str(filename)
                subprocess.check_call(["convert", temp.name, filename])

            return False

    def file_browse(self, action, name="", ext="", ext_name=""):
        if (action == gtk.FILE_CHOOSER_ACTION_OPEN):
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                       gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        else:
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                       gtk.STOCK_SAVE, gtk.RESPONSE_OK)

        dialog = gtk.FileChooserDialog(title="Select File", action=action,
                                       buttons=buttons)
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
