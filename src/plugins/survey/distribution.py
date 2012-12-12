# -*- coding:utf-8 -*-
# Copyright © 2012 Clément Schaff, Mahdi Ben Jelloul

"""
openFisca, Logiciel libre de simulation du système socio-fiscal français
Copyright © 2011 Clément Schaff, Mahdi Ben Jelloul

This file is part of openFisca.

    openFisca is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    (at your option) any later version.

    openFisca is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with openFisca.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import division
import numpy as np
from pandas import DataFrame, merge
from PyQt4.QtGui import (QWidget, QDockWidget, QVBoxLayout, QHBoxLayout, QComboBox, QSortFilterProxyModel,
                         QSpacerItem, QSizePolicy, QApplication, QCursor, QPushButton, QInputDialog)
from PyQt4.QtCore import SIGNAL, Qt, QSize
from core.qthelpers import OfSs, DataFrameViewWidget
from core.qthelpers import MyComboBox, get_icon
from core.simulation import SurveySimulation


class OFPivotTable(object):
    def __init__(self):
        super(OFPivotTable, self).__init__()
        
        self.data = DataFrame() # Pandas DataFrame
        self.data_default   = None
        self.by_var_choices = None
        
        # List of variable entering the level 0 (rows) index
        self.row_index = None
        
        # TODO:
        # Dict of variables in the level 1 (columns)
        # exemple { revdisp : { data : [ 'current', 'default'], transform : ['mean', 'median'],  diff: ['absolute', 'relative', 'winners', 'loosers']
    
    
    def set_simulation(self, simulation):
        if isinstance(simulation, SurveySimulation):
            self.simulation = simulation
            self.by_var_choices = self.simulation.var_list
        else:
            raise Exception('Aggreaates:  %s should be an instance of %s class'  %(simulation, SurveySimulation))

    @property
    def vars(self):
        return set(self.simulation.var_list)

    def set_data(self, output_data, default=None):
        self.data = output_data
        if default is not None:
            self.data_default = default
        self.wght = self.data['wprm']

    def get_table(self, by = None, vars = None):
        '''
        Updated frame
        '''
        by_var = by
        if by_var is None:
            raise Exception("OFPivotTable : get_table needs a 'by' variable")
        
        if vars is None:
            raise Exception("OFPivotTable : get_table needs a 'vars' variable")

        initial_set = set([by_var, 'champm'])
        
        data, data_default = self.simulation.aggregated_by_household(initial_set)
        self.set_data(data, data_default)        
        
        dist_frame_dict = self.group_by(vars, by_var)
        
        frame = None
        for dist_frame in dist_frame_dict.itervalues():
            if frame is None:
                frame = dist_frame.copy()
            else:
                dist_frame.pop('wprm')
                frame = merge(frame, dist_frame, on=by_var)
                
        by_var_label = self.simulation.var2label[by_var]
        if by_var_label == by_var:
            by_var_label = by_var

        enum = self.simulation.var2enum[by_var]                
        
        
        frame = frame.reset_index(drop=True)
        
        for col in frame.columns:
            if col[-6:] == "__init":
                frame.rename(columns = { col : self.simulation.var2label[col[:-6]] + " init."}, inplace = True) 
            else:
                frame.rename(columns = { col : self.simulation.var2label[col] }, inplace = True)
        
        frame[by_var_label] = frame[by_var_label].apply(lambda x: enum._vars[x])
               
        return frame
     
    
    def group_by2(self, varlist, category):
        '''
        Computes grouped aggregates
        '''
        datasets = {'data': self.data}
        aggr_dict = {}
    
        if self.data_default is not None:
            datasets['default'] = self.data_default
            
        cols = self.cols
        # cols = []

        for name, data in datasets.iteritems():
            # Computes aggregates by category
            keep = [category, 'wprm', 'champm'] + cols
            temp_data = data[keep].copy()
            temp_data['wprm'] = temp_data['wprm']*temp_data['champm']
            keep.remove('champm')
            del keep['champm']
            temp = []
            for var in varlist:
                temp_data[var] = temp_data['wprm']*data[var]
                temp.append(var)
                keep.append(var)
                    
            from pandas import pivot_table
            aggr_dict[name] = pivot_table(temp_data[keep], cols = cols,
                                  rows = category, values=keep, aggfunc = np.sum)
            
            for cat, df in aggr_dict[name].iterrows():
                for varname in varlist:
                    if name=='default':
                        label = varname + '__init'
                        df[label] = df[varname]/df['wprm']
                        del df[varname]
                    else:
                        df[varname] = df[varname]/df['wprm']
            
            aggr_dict[name].index.names[0] = 'variable'
            aggr_dict[name] = aggr_dict[name].reset_index().unstack(cols.insert(0, 'variable'))

            
        return aggr_dict

    def group_by(self, varlist, category):
        '''
        Computes grouped aggregates
        '''
        datasets = {'data': self.data}
        aggr_dict = {}
        if self.data_default is not None:
            datasets['default'] = self.data_default

        for name, data in datasets.iteritems():
            # Computes aggregates by category
            keep = [category, 'wprm', 'champm'] 
            temp_data = data[keep].copy()
            temp_data['wprm'] = temp_data['wprm']*temp_data['champm']
            keep.remove('champm')
            del temp_data['champm']
            temp = []
            for var in varlist:
                temp_data[var] = temp_data['wprm']*data[var]
                temp.append(var)
                keep.append(var)
                
            
            grouped = temp_data[keep].groupby(category, as_index = False)
            aggr_dict[name] = grouped.aggregate(np.sum)

            # Normalizing to have the average
            for varname in temp:
                if name=='default':
                    label = varname + '__init'
                    aggr_dict[name][label] = aggr_dict[name][varname]/aggr_dict[name]['wprm']
                    del aggr_dict[name][varname]
                else:
                    aggr_dict[name][varname] = aggr_dict[name][varname]/aggr_dict[name]['wprm']
                              
        return aggr_dict


    def clear(self):

        self.view.clear()
        self.data = None
        self.wght = None


    
class DistributionWidget(QDockWidget):
    def __init__(self, parent = None):
        super(DistributionWidget, self).__init__(parent)
        self.setStyleSheet(OfSs.dock_style)
        # Create geometry
        self.setObjectName("Distribution")
        self.setWindowTitle("Distribution")
        self.dockWidgetContents = QWidget()
        
        self.distribution_combo = MyComboBox(self.dockWidgetContents, u"Distribution de l'impact par")
        self.distribution_combo.box.setSizeAdjustPolicy(self.distribution_combo.box.AdjustToContents)
        self.distribution_combo.box.setDisabled(True)
        
        # To enable sorting of the combobox
        # hints from here: http://www.qtcentre.org/threads/3741-How-to-sort-a-QComboBox-in-Qt4
        #        and here: http://www.pyside.org/docs/pyside/PySide/QtGui/QSortFilterProxyModel.html      
        proxy = QSortFilterProxyModel(self.distribution_combo.box)
        proxy.setSourceModel(self.distribution_combo.box.model())
        self.distribution_combo.box.model().setParent(proxy)
        self.distribution_combo.box.setModel(proxy)
        
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        add_var_btn  = self.add_toolbar_btn(tooltip = u"Ajouter une variable de calage",
                                        icon = "list-add.png")
        
        rmv_var_btn = self.add_toolbar_btn(tooltip = u"Retirer une variable de calage",
                                        icon = "list-remove.png")

        toolbar_btns = [add_var_btn, rmv_var_btn] #rst_var_btn
        

        distribLayout = QHBoxLayout()
        for btn in toolbar_btns:
            distribLayout.addWidget(btn)
        distribLayout.addWidget(self.distribution_combo)
        distribLayout.addItem(spacerItem)
        
        self.view = DataFrameViewWidget(self.dockWidgetContents)



        
                
        verticalLayout = QVBoxLayout(self.dockWidgetContents)
        verticalLayout.addLayout(distribLayout)
        verticalLayout.addWidget(self.view)
                
        self.setWidget(self.dockWidgetContents)


        self.connect(add_var_btn, SIGNAL('clicked()'), self.add_var)
        self.connect(rmv_var_btn, SIGNAL('clicked()'), self.remove_var)

        # Initialize attributes
        self.parent = parent
        self.of_pivot_table = None
        self.distribution_by_var = None
        self.selected_vars = None
        
        self.initialize()

    def add_toolbar_btn(self, tooltip = None, icon = None):
        btn = QPushButton(self)
        if tooltip:
            btn.setToolTip(tooltip)
        if icon:
            icn = get_icon(icon)
            btn.setIcon(icn)
            btn.setIconSize(QSize(22, 22))
        return btn

    def initialize(self):
        
        self.distribution_by_var = 'so'
        self.selected_vars = set(['revdisp', 'nivvie']) 
        

    def set_of_pivot_table(self, of_pivot_table):
        self.of_pivot_table = of_pivot_table
        self.vars = self.of_pivot_table.vars
        self.set_distribution_choices()
    
    def add_var(self):
        var = self.ask()
        if var is not None:
            self.selected_vars.add(var)
            self.refresh_plugin()
        else:
            return
    
    def remove_var(self):
        var = self.ask(remove=True)
        if var is not None:
            self.selected_vars.remove(var)
            self.refresh_plugin()
        else:
            return

    def ask(self, remove=False):
        if not remove:
            dialog_label = "Ajouter une variable"
            choices = self.vars - self.selected_vars
        else:
            choices =  self.selected_vars
            dialog_label = "Retirer une variable"
            
        dialog_choices = sorted([self.of_pivot_table.simulation.var2label[variab] for variab in list(choices)])
        label, ok = QInputDialog.getItem(self, dialog_label , "Choisir la variable", 
                                       dialog_choices)
        if ok and label in dialog_choices:
            return self.of_pivot_table.simulation.label2var[unicode(label)] 
        else:
            return None 

    def dist_by_changed(self):    
        widget = self.distribution_combo.box
        if isinstance(widget, QComboBox):
            data = widget.itemData(widget.currentIndex())
            by_var = unicode(data.toString())
            self.distribution_by_var = by_var                
            self.refresh_plugin()
                     
    def set_distribution_choices(self):
        '''
        Set the variables appearing in the ComboBox 
        '''
        combobox = self.distribution_combo.box
        combobox.setEnabled(True)
        self.disconnect(combobox, SIGNAL('currentIndexChanged(int)'), self.dist_by_changed)
        self.distribution_combo.box.clear()
        
        if self.of_pivot_table is not None:
            choices = set( self.of_pivot_table.by_var_choices )
            var2label = self.of_pivot_table.simulation.var2label
        else:
            choices = []
        
        for var in choices:
            combobox.addItem(var2label[var], var )

        if hasattr(self, 'distribution_by_var'):
            index = combobox.findData(self.distribution_by_var)
            if index != -1:
                combobox.setCurrentIndex(index)
        
        self.connect(self.distribution_combo.box, SIGNAL('currentIndexChanged(int)'), self.dist_by_changed)
        self.distribution_combo.box.model().sort(0)

    def refresh_plugin(self):
        '''
        Update distribution view
        '''
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
        by_var = self.distribution_by_var
        selection = self.selected_vars 
        frame = self.of_pivot_table.get_table(by = by_var, vars = selection)
        
        self.view.set_dataframe(frame)
        self.view.reset()
        self.calculated()

        QApplication.restoreOverrideCursor()

    def calculated(self):
        '''
        Emits signal indicating that aggregates are computed
        '''
        self.emit(SIGNAL('calculated()'))
