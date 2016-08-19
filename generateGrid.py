# -*- coding: utf-8 -*-
"""
Created on 21/06/2016

@author: Charlie Bourigault
@contact: bourigault.charlie@gmail.com

Please report issues and request on the GitHub project from ChrisEberl (Python_DIC)
More details regarding the project on the GitHub Wiki : https://github.com/ChrisEberl/Python_DIC/wiki

Current File: This file manages the complete grid creation tool with controls, filters and shift correction
"""

from PySide.QtCore import *
from PySide.QtGui import *

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor
import cv2
import matplotlib.figure
import matplotlib.patches
import numpy as np
import progressWidget
import newProcessCorrelations
import StrainAnalysis
import time
import filterWidget
import getData




def createGrid(mainWindow): #start the generateGrid widget and put it in the main window
    
    imageFileList = []
    fileList = open(mainWindow.fileDataPath+'/filenamelist.dat',"r")
    for element in fileList:
        imageFileList.append(element)

    gridWidget = generateGridWidget(mainWindow, imageFileList)
    
    mainWindow.setCentralWidget(gridWidget)
    
    gridWidget.topWidget.prepareTools(imageFileList)



class generateGridWidget(QWidget):
    
    def __init__(self, parentWindow, imageFileList):  #initiate the generateGrid Widget
    
        super(generateGridWidget, self).__init__()
        
        self.parentWindow = parentWindow
        self.markerInstances = []
        self.imageFileList = imageFileList
        self.currentImage = []
        self.contourCenter = []
        self.imageActiveList = np.ones((len(self.imageFileList)))
        
        mainLayout = QVBoxLayout() #Setting vertical mainLayout
        mainLayout.setAlignment(Qt.AlignCenter)
        
        topWidgetContainer = QWidget()
        self.topWidgetStackedLayout = QStackedLayout()
        
        self.topWidget = topToolsWidget(self) #Creating the top tools widget and adding it to the stackedLayout
        
        calculationWidget = QWidget()
        calculationLayout = QHBoxLayout()
        self.calculationBar = progressWidget.progressBarWidget(minimumWidth=250, maximumWidth=600, minimumHeight=20, maximumHeight=50, title='Starting Processes...') #progressBar widget stacked with topWidget and shown when starting the processCorrelation
        calculationLayout.addStretch(1)
        calculationLayout.addWidget(self.calculationBar)
        calculationLayout.addStretch(1)
        calculationWidget.setLayout(calculationLayout)

        self.topWidgetStackedLayout.addWidget(self.topWidget)
        self.topWidgetStackedLayout.addWidget(calculationWidget)
        topWidgetContainer.setLayout(self.topWidgetStackedLayout)
        
        mainBottomWidget = QWidget() #create bottom widget and horizontal layout
        self.mainBottomLayout = QHBoxLayout()
        self.mainBottomLayout.setContentsMargins(0,0,0,0)
        
        self.figureDisplayWidget = matplotlibWidget() #create matplotlib and filter widgets
        self.filterToolWidget = filterWidget.filterCreationWidget(self)
        #filterToolWidget.setDisabled(True)
        self.figureDisplayWidget.setFocusPolicy(Qt.ClickFocus) #activate mouse events on the matplotlib figure
        self.figureDisplayWidget.setFocus()
        self.pressEvent = self.figureDisplayWidget.mpl_connect('button_press_event', self.canvasPress) #activate button events
        
        self.mainBottomLayout.addWidget(self.figureDisplayWidget) #adding the two newly created widget to the horizontal layout
        self.mainBottomLayout.addWidget(self.filterToolWidget)
        
        mainBottomWidget.setLayout(self.mainBottomLayout) #setting the horizontal layout to the bottom widget
        
        mainLayout.addWidget(topWidgetContainer)
        mainLayout.addWidget(mainBottomWidget) #adding the bottom widget to the main vertical layout
        mainLayout.addStretch(1)
        
        self.setLayout(mainLayout)
        
    def plotImage(self, filterPreview=None): #plot the image and detected contour if auto selection mode on
    
        currentImage = self.topWidget.currentImageValue.value()-1
        imagePath = self.parentWindow.filePath+'/'+self.imageFileList[currentImage]
        self.figureDisplayWidget.imagePlot.cla()
        imageFile = cv2.imread(imagePath.rstrip(), 0) #converting image to gray scale

        #applying filters
        imageFile = filterWidget.applyFilterListToImage(self.filterToolWidget.appliedFiltersList, imageFile)
        
        try:
            if filterPreview is not None:
                imageFile = filterWidget.applyFilterToImage(filterPreview[0], filterPreview[1:4], imageFile)
        except:
            pass
        
        #histogram
        self.filterToolWidget.histoPlot.plot.cla()
        self.filterToolWidget.histoPlot.plot.hist(imageFile.flatten(), bins=32, color='black')
        self.filterToolWidget.histoPlot.plot.set_xlim([0,255])
        self.filterToolWidget.histoPlot.plot.set_yticklabels([])
        self.filterToolWidget.histoPlot.draw()
        
        if self.imageActiveList[currentImage] == 1: #image non deleted by the user
            self.topWidget.imageActiveBox.setChecked(True)
            self.topWidget.autoWidget.setEnabled(True)
            self.topWidget.centerToolWidget.setEnabled(True)
            self.contourCenter = []
            minContourSize = 0
            # Contours detection
            if self.topWidget.addGridButton.isEnabled():
                if self.topWidget.invertRange.isChecked():
                    ret,thresh = cv2.threshold(imageFile,self.topWidget.rangeSlider.value(),255,1) #apply inverted binary threshold
                else:
                    ret,thresh = cv2.threshold(imageFile,self.topWidget.rangeSlider.value(),255,0) #apply binary threshold
                image, contours, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
                minContourSize = self.topWidget.sizeSlider.value()
                for contour in contours:
                    if cv2.contourArea(contour, True) > minContourSize: #keeping only contour where the area is more than the min area chose by the user with the size slider
                        M = cv2.moments(contour)
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])
                        self.contourCenter.append([cX,cY])
                self.topWidget.elementsValue.setText(str(len(self.contourCenter)))
                
            self.currentImage = self.figureDisplayWidget.imagePlot.imshow(imageFile, cmap='gray', vmin=0, vmax=255)
            
            
            squareLenght = minContourSize**(1/2.0)
            for element in self.contourCenter: #drawing squares in each detected contour location
                corner = (element[0]-squareLenght/2,element[1]-squareLenght/2)
                square = matplotlib.figure.Rectangle(corner, squareLenght, squareLenght, facecolor='None', edgecolor='green', linewidth=1.5)
                self.figureDisplayWidget.imagePlot.add_patch(square)
            
            self.figureDisplayWidget.draw()
            if self.topWidget.centerToolWidget.isEnabled():
                self.refreshMarkers()
                
        else: #image deleted by the user
        
            self.topWidget.autoWidget.setDisabled(True)
            self.topWidget.centerToolWidget.setDisabled(True)
            self.topWidget.imageActiveBox.setChecked(False)
            ax = self.figureDisplayWidget.imagePlot
            ax.set_axis_bgcolor('black')
            ax.text(.5, .5, 'Removed.', ha='center', va='center', transform = ax.transAxes, color='red')
            self.figureDisplayWidget.draw()
        
    def canvasPress(self, event): #triggered when a click is made on the image
        
        self.x0 = event.xdata
        self.y0 = event.ydata
        if self.x0 is None: #return when click is made outside the image
            return
           
        if self.filterToolWidget.availableFilters.currentItem() is not None:
            if self.filterToolWidget.availableFilters.currentItem().text() == 'Zoom':
                self.filterToolWidget.parameterValues[2].setText(str(int(self.x0))+','+str(int(self.y0)))
            
        if self.topWidget.shiftCorrectionBox.isChecked() and self.topWidget.centerToolWidget.isEnabled() == False: #when drawing a rectangle for shift correction
            
            self.rect = matplotlib.figure.Rectangle((self.x0, self.y0), 10, 10, facecolor='None', edgecolor='green', linewidth=2.5)
            self.figureDisplayWidget.imagePlot.add_patch(self.rect)
            self.figureDisplayWidget.draw_idle()
            self.motion = self.figureDisplayWidget.mpl_connect('motion_notify_event', self.motionEvent) #activate the motion event and call on_motion function for each movement of the mouse
            
        if self.topWidget.rectangleSelection.isChecked(): #when drawing an area to create a rectangle grid
            
            self.rect = matplotlib.figure.Rectangle((self.x0, self.y0), 10, 10, facecolor='None', edgecolor='green', linewidth=2.5)
            self.figureDisplayWidget.imagePlot.add_patch(self.rect)
            self.figureDisplayWidget.draw_idle()
            self.motion = self.figureDisplayWidget.mpl_connect('motion_notify_event', self.motionEvent) #activate the motion event and call on_motion function for each movement of the mouse
            
        if self.topWidget.ellipseSelection.isChecked(): #when drawing an area to create an ellipsoidal grid

            self.ellipse = matplotlib.patches.Ellipse((self.x0, self.y0), 10, 10, 0, color='green', fill=False, linewidth=2.5)
            self.figureDisplayWidget.imagePlot.add_patch(self.ellipse)
            self.figureDisplayWidget.draw_idle()
            self.motion = self.figureDisplayWidget.mpl_connect('motion_notify_event', self.motionEvent) #activate the motion event and call on_motion function for each movement of the mouse
            
        if self.topWidget.selectManualButton.isChecked(): #when clicking on the image to mode one element/grid instance
            
            self.selectedInstance = -1
            nb = -1
            for element in self.markerInstances:
                nb += 1
                if len(np.atleast_1d(element[0])) < 1:
                    continue
                lowLimitX = np.nanmin(element[0])-10
                highLimitX = np.nanmax(element[0])+10
                lowLimitY = np.nanmin(element[1])-10
                highLimitY = np.nanmax(element[1])+10
                if self.x0 > lowLimitX and self.x0 < highLimitX: #taking the first instance fullfilling the criterias to be selected
                    if self.y0 > lowLimitY and self.y0 < highLimitY:
                        self.selectedInstance = nb
                        break
            
            if self.selectedInstance > -1: #drawing a rectangle to follow the displacement of the element by the user
                self.rectCenter = (lowLimitX, lowLimitY)
                self.rect = matplotlib.figure.Rectangle(self.rectCenter, highLimitX-lowLimitX, highLimitY-lowLimitY, facecolor='None', edgecolor='green', linewidth=2.5)
                self.figureDisplayWidget.imagePlot.add_patch(self.rect)
                self.figureDisplayWidget.draw_idle()
                self.motion = self.figureDisplayWidget.mpl_connect('motion_notify_event', self.motionEvent) #activate the motion event and call on_motion function for each movement of the mouse
            
        if self.topWidget.addManualButton.isChecked():
            
            self.markerInstances.append([np.array(self.x0), np.array(self.y0)]) #add a single marker to the list of elements
            self.refreshMarkers()
            
        if self.topWidget.removeManualButton.isChecked():
            
            self.rect = matplotlib.figure.Rectangle((self.x0, self.y0), 10, 10, facecolor='None', edgecolor='green', linewidth=2.5)
            self.figureDisplayWidget.imagePlot.add_patch(self.rect)
            self.figureDisplayWidget.draw_idle()
            self.motion = self.figureDisplayWidget.mpl_connect('motion_notify_event', self.motionEvent) #activate the motion event and call on_motion function for each movement of the mouse
        
        
    def motionEvent(self, event): #triggered every time the user moves the mouse on the image
        
        x1 = event.xdata
        y1 = event.ydata
        if x1 is None: #in case the mouse goes outside the canvas, return
            return
        self.width = x1 - self.x0
        self.height = y1 - self.y0
        
        
        if self.topWidget.shiftCorrectionBox.isChecked() and self.topWidget.centerToolWidget.isEnabled() == False:
            
            self.rect.set_width(self.width)
            self.rect.set_height(self.height)
            self.rect.set_linestyle('dashed')
            
        if self.topWidget.rectangleSelection.isChecked():
            
            self.rect.set_width(self.width)
            self.rect.set_height(self.height)
            self.rect.set_linestyle('dashed')

        if self.topWidget.ellipseSelection.isChecked():
            
            self.ellipse.remove()
            self.ellipse = matplotlib.patches.Ellipse((.5*(self.x0+x1), .5*(self.y0+y1)), self.width, self.height, 0, color='green', fill=False, linewidth=2.5)
            self.ellipse.set_linestyle('dashed')
            self.figureDisplayWidget.imagePlot.add_patch(self.ellipse)
            
        if self.topWidget.selectManualButton.isChecked():
            
            newCoordinates = tuple(np.array(self.rectCenter) + np.array((self.width,self.height)))
            self.rect.set_xy(newCoordinates)
            self.rect.set_linestyle('dashed')
            
        if self.topWidget.removeManualButton.isChecked():
            
            self.rect.set_width(self.width)
            self.rect.set_height(self.height)
            self.rect.set_linestyle('dashed')
            
        self.figureDisplayWidget.draw_idle()
        self.canvasRelease = self.figureDisplayWidget.mpl_connect('button_release_event', self.releaseEvent)
            
    def releaseEvent(self, event): #triggered when the user release the mouse button
        
        self.figureDisplayWidget.mpl_disconnect(self.motion) #deactivate the motion event
        self.figureDisplayWidget.mpl_disconnect(self.canvasRelease) #deactive the mouse release event
        
        if self.topWidget.shiftCorrectionBox.isChecked() and self.topWidget.centerToolWidget.isEnabled() == False:
            
            self.topWidget.infosButtonsLayout.setCurrentIndex(1) #change the stacked layout for displaying Track button instead of Process
            self.topWidget.trackButton.setEnabled(True)
            self.topWidget.trackButton.setText('Track')
        
        if self.topWidget.rectangleSelection.isChecked():

            self.rect.remove()
            self.newMarkers()
            
        if self.topWidget.ellipseSelection.isChecked():

            self.ellipse.remove()
            self.newMarkers()
            
        if self.topWidget.selectManualButton.isChecked():
            
            self.rect.remove()
            self.markerInstances[self.selectedInstance][0] += self.width
            self.markerInstances[self.selectedInstance][1] += self.height
            self.plotImage()
        
        if self.topWidget.removeManualButton.isChecked():
            
            self.rect.remove()
            self.deleteMarkers()
            
            
    def openGrid(self):
        
        flags = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly #ask for a directory
        gridDirectory = QFileDialog.getExistingDirectory(self, 'Data Folder containing grid files', '', flags)
    
        if gridDirectory == "":
            return
        else:
            #Test if files exists and extract data

            gridX_entities = getData.getDataFromFile([gridDirectory+'/gridx.dat'], 0, singleColumn=1)
            gridY_entities = getData.getDataFromFile([gridDirectory+'/gridy.dat'], 0, singleColumn=1)
            
            if gridX_entities is None or gridY_entities is None:
                errorMessage = QMessageBox()
                errorMessage.setWindowTitle('Error')
                errorMessage.setText('Grid not found.')
                errorMessage.exec_()
                return
                
            gridX = []
            gridY = []
            instanceList = []
            if type(gridX_entities[0]) <> np.void:
                gridX_entities_temp = []
                gridY_entities_temp = []
                for element in gridX_entities:
                    gridX_entities_temp.append((element, 0))
                for element in gridY_entities:
                    gridY_entities_temp.append((element, 0))
                gridX_entities = gridX_entities_temp
                gridY_entities = gridY_entities_temp
            for (coords, instance) in gridX_entities:
                gridX.append(coords)
                instanceList.append(instance)
            for (coords, instance) in gridY_entities:
                gridY.append(coords)
            
            gridX = np.array(gridX)
            gridY = np.array(gridY)
            
            for instance in np.unique(instanceList):
                currentList = []
                nb = 0
                for element in instanceList:
                    if element == instance:
                        currentList.append(nb)
                    nb+=1
                if len(np.atleast_1d(currentList)) > 0:
                    self.markerInstances.append([gridX[currentList], gridY[currentList]])

            self.refreshMarkers()
    
    def openFilter(self):
        
        flags = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly #ask for a directory
        filterDirectory = QFileDialog.getExistingDirectory(self, 'Data Folder containing filter file', '', flags)
    
        if filterDirectory == "":
            return
        else:
            #Test if files exists and extract data
            filterList = filterWidget.saveOpenFilter(filterDirectory)
            if filterList is not None:
                self.filterToolWidget.appliedFiltersList = filterList.tolist()
            else:
                errorMessage = QMessageBox()
                errorMessage.setWindowTitle('Error')
                errorMessage.setText('filter.dat not found.')
                errorMessage.exec_()
                return
            
            self.filterToolWidget.refreshAppliedFilters()
            self.plotImage()
            
            
    def newMarkers(self): #adding new marnkers to the list of marker instances
        
        nbMarkersX = self.topWidget.nbMarkersX.value()
        nbMarkersY = self.topWidget.nbMarkersY.value()
        totalMarkers = nbMarkersX*nbMarkersY
        xMarkers = np.linspace(self.x0, self.x0+self.width, nbMarkersX)
        yMarkers = np.linspace(self.y0, self.y0+self.height, nbMarkersY)
        [X,Y] = np.meshgrid(xMarkers, yMarkers) #create rectangle grid
        
        if self.topWidget.ellipseSelection.isChecked(): #remove markers outside the ellipse in the grid by setting them to nan values
            for markerX in range(nbMarkersX):
                for markerY in range(nbMarkersY):
                    if (X[markerY][markerX]-.5*(self.x0+self.x0+self.width))**2/(self.width/2)**2 + (Y[markerY][markerX]-.5*(self.y0+self.y0+self.height))**2/(self.height/2)**2 > 1.0:
                        X[markerY][markerX] = np.nan
                        Y[markerY][markerX] = np.nan
                        
        gridX = np.reshape(X, totalMarkers, 1)
        gridY = np.reshape(Y, totalMarkers, 1)
        
        markersToDelete = []
        for marker in range(totalMarkers): #add each nan value marker to the list of markers to delete
            if np.isnan(gridX[marker]):
                markersToDelete.append(marker)
        gridX = np.delete(gridX, markersToDelete)
        gridY = np.delete(gridY, markersToDelete)
        
        xCoords = 0
        yCoords = 0
        if self.topWidget.shiftCorrectionBox.isChecked() and self.topWidget.largeDisp is not None: #if a shift correction as been made, remove it from the coordinates to have the original grid coordinate
            xCoords = float(self.topWidget.shiftCorrX.text())
            yCoords = float(self.topWidget.shiftCorrY.text())
            
        self.markerInstances.append([gridX-xCoords, gridY-yCoords]) #save the coordinates of markers into the list of marker instances variable
        self.refreshMarkers()
        
    def addGrid(self): #triggered when the auto selection if accepted by the user, it places a grid on each contour detected 
        
        self.topWidget.addGridButton.setDisabled(True)
        self.topWidget.sizeWidget.setDisabled(True)
        self.topWidget.rangeWidget.setDisabled(True)
        self.topWidget.elementsWidget.setDisabled(True)
        squareLenght = self.topWidget.sizeSlider.value()**(1/2.0)
        for element in self.contourCenter:
            self.x0 = element[0]-squareLenght/2
            self.y0 = element[1]-squareLenght/2
            self.width = squareLenght
            self.height = squareLenght
            self.newMarkers()
        self.topWidget.buttonClicked(0)
        
    def deleteMarkers(self): #delete markers in the area selected by the user
        
        xCoords = 0  #shift correction
        yCoords = 0
        if self.topWidget.shiftCorrectionBox.isChecked() and self.topWidget.largeDisp is not None: #apply the shift if the user select markers shifted in the current image
            xCoords = float(self.topWidget.shiftCorrX.text())
            yCoords = float(self.topWidget.shiftCorrY.text())
            
        lowLimitX = self.x0 - xCoords
        highLimitX = self.x0 + self.width - xCoords
        lowLimitY = self.y0 - yCoords
        highLimitY = self.y0 + self.height - yCoords
        for element in self.markerInstances:
            nbMarkers = len(np.atleast_1d(element[0]))
            markersToDelete = []
            if nbMarkers < 2:
                if element[0] > np.nanmin([lowLimitX,highLimitX]) and element[0] < np.nanmax([lowLimitX,highLimitX]):
                    if element[1] > np.nanmin([lowLimitY,highLimitY]) and element[1] < np.nanmax([lowLimitY,highLimitY]):
                        markersToDelete.append(0)
            else:
                for marker in range(nbMarkers):
                    if element[0][marker] > np.nanmin([lowLimitX,highLimitX]) and element[0][marker] < np.nanmax([lowLimitX,highLimitX]):
                        if element[1][marker] > np.nanmin([lowLimitY,highLimitY]) and element[1][marker] < np.nanmax([lowLimitY,highLimitY]):
                            markersToDelete.append(marker)
            element[0] = np.delete(element[0], markersToDelete)
            element[1] = np.delete(element[1], markersToDelete)
        
        self.plotImage()
                    
    
    def refreshMarkers(self): #take all the markers in the list of marker instances and plot them
        
        self.figureDisplayWidget.imagePlot.autoscale(False)
        nbMarkers = 0
        xCoords = 0
        yCoords = 0
        if self.topWidget.shiftCorrectionBox.isChecked() and self.topWidget.largeDisp is not None: #apply the shift correction to the plotted markers
            xCoords = float(self.topWidget.shiftCorrX.text())
            yCoords = float(self.topWidget.shiftCorrY.text())
            
        for element in self.markerInstances:
            nbMarkers += len(np.atleast_1d(element[0]))
            self.figureDisplayWidget.imagePlot.plot(element[0]+xCoords, element[1]+yCoords, '+r')
        
        if nbMarkers > 2: #minimum 3 markers needed to start the processing
            self.topWidget.processButton.setEnabled(True)
        else:
            self.topWidget.processButton.setDisabled(True)
        self.topWidget.totalMarkersValue.setText(str(nbMarkers))
        self.figureDisplayWidget.draw_idle()        
        
class topToolsWidget(QWidget): #contains the different tools to create the grid, add and remove markers, start the analysis
    
    def __init__(self, parentWidget):
        
        super(topToolsWidget, self).__init__()
                
        self.parentWidget = parentWidget
        horizontalLayout = QHBoxLayout()
        self.setMaximumHeight(150)
        self.largeDisp = None
        self.lastTime = 0 #variable used for time calculation
        
        #LEFT PART OF THE TOOL WIDGET : Automatic Mode
        
        self.autoWidget = QWidget()
        autoLayout = QVBoxLayout()
        autoLayout.setAlignment(Qt.AlignCenter)
        autoLayout.setContentsMargins(0,0,0,0)
        
        buttonsWidget = QWidget()
        buttonsLayout = QHBoxLayout()
        buttonsLayout.setContentsMargins(0,0,0,0)
        self.autoButton = QPushButton('Auto Select.')
        self.autoButton.setCheckable(True)
        self.autoButton.pressed.connect(lambda: self.buttonClicked(self.autoButton))
        self.addGridButton = QPushButton('Add Grid')
        self.addGridButton.setDisabled(True)
        self.addGridButton.clicked.connect(self.parentWidget.addGrid)
        buttonsLayout.addWidget(self.autoButton)
        buttonsLayout.addWidget(self.addGridButton)
        buttonsWidget.setLayout(buttonsLayout)
        
        
        self.sizeWidget = QWidget()
        self.sizeWidget.setDisabled(True)
        sizeLayout = QHBoxLayout()
        sizeLayout.setContentsMargins(0,0,0,0)
        sizeLbl = QLabel('Size:')
        self.sizeSlider = QSlider(Qt.Horizontal)
        self.sizeSlider.valueChanged.connect(self.parentWidget.plotImage)
        sizeLayout.addWidget(sizeLbl)
        sizeLayout.addWidget(self.sizeSlider)
        self.sizeWidget.setLayout(sizeLayout)
        
        self.rangeWidget = QWidget()
        self.rangeWidget.setDisabled(True)
        rangeLayout = QHBoxLayout()
        rangeLayout.setContentsMargins(0,0,0,0)
        rangeLbl = QLabel('Range:')
        self.rangeSlider = QSlider(Qt.Horizontal)
        self.rangeSlider.valueChanged.connect(self.parentWidget.plotImage)
        rangeLayout.addWidget(rangeLbl)
        rangeLayout.addWidget(self.rangeSlider)
        self.rangeWidget.setLayout(rangeLayout)
        
        self.elementsWidget = QWidget()
        self.elementsWidget.setDisabled(True)
        elementsLayout = QHBoxLayout()
        elementsLayout.setContentsMargins(0,0,0,0)
        elementsLbl = QLabel('Elements:')
        self.elementsValue = QLabel('-')
        self.invertRange = QCheckBox('Invert')
        self.invertRange.stateChanged.connect(self.parentWidget.plotImage)
        elementsLayout.addWidget(elementsLbl)
        elementsLayout.addWidget(self.elementsValue)
        elementsLayout.addWidget(self.invertRange)
        self.elementsWidget.setLayout(elementsLayout)

        autoLayout.addWidget(buttonsWidget)
        autoLayout.addWidget(self.sizeWidget)
        autoLayout.addWidget(self.rangeWidget)
        autoLayout.addWidget(self.elementsWidget)
        self.autoWidget.setLayout(autoLayout)
        
        #CENTER PART OF THE TOOL WIDGET : Tools + Parameters
        
        self.centerToolWidget = QWidget()
        centerToolLayout = QHBoxLayout()
        centerToolLayout.setAlignment(Qt.AlignCenter)
        centerToolLayout.setContentsMargins(0,0,0,0)
        
        
        shapeWidget = QWidget()
        shapeLayout = QVBoxLayout()
        shapeLayout.setContentsMargins(0,0,0,0)
        
        buttonsWidget = QWidget()
        buttonsLayout = QHBoxLayout()
        self.rectangleSelection = QPushButton('Rectangle')
        self.rectangleSelection.setCheckable(True)
        self.rectangleSelection.clicked.connect(lambda: self.buttonClicked(self.rectangleSelection))
        self.ellipseSelection = QPushButton('Ellipse')
        self.ellipseSelection.setCheckable(True)
        self.ellipseSelection.pressed.connect(lambda: self.buttonClicked(self.ellipseSelection))
        buttonsLayout.addWidget(self.rectangleSelection)
        buttonsLayout.addWidget(self.ellipseSelection)
        buttonsWidget.setLayout(buttonsLayout)
        
        gridSizeWidget = QWidget()
        gridSizeLayout = QHBoxLayout()
        gridSizeLayout.setContentsMargins(0,0,0,0)
        gridSizeLbl = QLabel('Grid Shape:')
        self.nbMarkersX = QSpinBox()
        gridSizeLbl_x = QLabel('x')
        gridSizeLbl_x.setAlignment(Qt.AlignCenter)
        self.nbMarkersY = QSpinBox()
        gridSizeLayout.addWidget(gridSizeLbl)
        gridSizeLayout.addWidget(self.nbMarkersX)
        gridSizeLayout.addWidget(gridSizeLbl_x)
        gridSizeLayout.addWidget(self.nbMarkersY)
        gridSizeWidget.setLayout(gridSizeLayout)
        
        self.shiftCorrectionWidget = QWidget()
        shiftCorrectionLayout = QHBoxLayout()
        shiftCorrectionLayout.setContentsMargins(0,0,0,0)
        shiftLbl = QLabel('Shift Corr.:')
        self.shiftCorrX = QLabel('-')
        self.shiftCorrX.setAlignment(Qt.AlignCenter)
        shiftLbl_x = QLabel('x')
        shiftLbl_x.setAlignment(Qt.AlignCenter)
        self.shiftCorrY = QLabel('-')
        self.shiftCorrY.setAlignment(Qt.AlignCenter)
        self.changeShiftButton = QPushButton('*')
        self.changeShiftButton.setMaximumWidth(20)
        self.changeShiftButton.clicked.connect(self.changeShift)
        shiftCorrectionLayout.addWidget(shiftLbl)
        shiftCorrectionLayout.addWidget(self.shiftCorrX)
        shiftCorrectionLayout.addWidget(shiftLbl_x)
        shiftCorrectionLayout.addWidget(self.shiftCorrY)
        shiftCorrectionLayout.addWidget(self.changeShiftButton)
        self.shiftCorrectionWidget.setLayout(shiftCorrectionLayout)
        self.shiftCorrectionWidget.setDisabled(True)
        
        shapeLayout.addWidget(buttonsWidget)
        shapeLayout.addWidget(gridSizeWidget)
        shapeLayout.addWidget(self.shiftCorrectionWidget)
        shapeWidget.setLayout(shapeLayout)
        
        
        singleManualWidget = QWidget()
        singleManualLayout = QVBoxLayout()
        singleManualLayout.setAlignment(Qt.AlignCenter)
        singleManualLayout.setContentsMargins(0,0,0,0)
        
        
        self.selectManualButton = QPushButton('<>')
        self.selectManualButton.setMaximumWidth(20)
        self.selectManualButton.setCheckable(True)
        self.selectManualButton.pressed.connect(lambda: self.buttonClicked(self.selectManualButton))
        self.addManualButton = QPushButton('+')
        self.addManualButton.setMaximumWidth(20)
        self.addManualButton.setCheckable(True)
        self.addManualButton.pressed.connect(lambda: self.buttonClicked(self.addManualButton))
        self.removeManualButton = QPushButton('-')
        self.removeManualButton.setMaximumWidth(20)
        self.removeManualButton.setCheckable(True)
        self.removeManualButton.pressed.connect(lambda: self.buttonClicked(self.removeManualButton))
        singleManualLayout.addWidget(self.selectManualButton)
        singleManualLayout.addWidget(self.addManualButton)
        singleManualLayout.addWidget(self.removeManualButton)
        singleManualWidget.setLayout(singleManualLayout)
        
        
        centerToolLayout.addWidget(shapeWidget)
        centerToolLayout.addWidget(singleManualWidget)
        
        self.centerToolWidget.setLayout(centerToolLayout)
        
        #RIGHT PART OF THE TOOL WIDGET : Infos + Process
        
        infosWidget = QWidget()
        infosLayout = QHBoxLayout()
        infosLayout.setAlignment(Qt.AlignCenter)
        infosLayout.setContentsMargins(0,0,0,0)
        
        
        labelWidget = QWidget()
        labelLayout = QVBoxLayout()
        labelLayout.setContentsMargins(0,0,0,0)
        
        totalImagesLbl = QLabel('Total Images:')
        totalMarkersLbl = QLabel('Total Markers:')
        corrsizeLbl = QLabel('CorrSize:')
        currentImageLbl = QLabel('Image:')
        
        labelLayout.addWidget(totalImagesLbl)
        labelLayout.addWidget(totalMarkersLbl)
        labelLayout.addWidget(corrsizeLbl)
        labelLayout.addWidget(currentImageLbl)
        labelWidget.setLayout(labelLayout)
        
        
        valueWidget = QWidget()
        valueLayout = QVBoxLayout()
        valueLayout.setAlignment(Qt.AlignHCenter)
        valueLayout.setContentsMargins(0,5,0,0)
        
        self.totalImagesValue = QLabel('-')
        self.totalImagesValue.setAlignment(Qt.AlignCenter)
        self.totalMarkersValue = QLabel('-')
        self.totalMarkersValue.setAlignment(Qt.AlignCenter)
        self.corrsizeValue = QSpinBox()
        
        
        currentImageWidget = QWidget()
        currentImageLayout = QHBoxLayout()
        currentImageLayout.setContentsMargins(0,0,0,0)
        self.imageActiveBox = QCheckBox()
        self.imageActiveBox.setChecked(True)
        self.imageActiveBox.stateChanged.connect(self.imageDeleted)
        self.currentImageValue = QSpinBox()
        self.currentImageValue.valueChanged.connect(self.imageChanged)
        currentImageLayout.addWidget(self.currentImageValue)
        currentImageLayout.addWidget(self.imageActiveBox)
        currentImageWidget.setLayout(currentImageLayout)

        
        valueLayout.addWidget(self.totalImagesValue)
        valueLayout.addSpacing(10)
        valueLayout.addWidget(self.totalMarkersValue)
        valueLayout.addWidget(self.corrsizeValue)
        valueLayout.addWidget(currentImageWidget)
        valueWidget.setLayout(valueLayout)
        
        
        processWidget = QWidget()
        processLayout = QVBoxLayout()
        processLayout.setAlignment(Qt.AlignCenter)
        processLayout.setContentsMargins(10,0,10,0)
        
    
        referenceLbl = QLabel('Reference')
        referenceLbl.setAlignment(Qt.AlignCenter)
        self.referenceImg = QComboBox()
        self.referenceImg.addItem('Previous Image')
        self.referenceImg.addItem('First Image')
        self.referenceImg.addItem('Shifted Ref.')
        self.referenceImg.setCurrentIndex(1)
        
        self.shiftCorrectionBox = QCheckBox('Shift Correction')
        self.shiftCorrectionBox.toggled.connect(lambda: self.shiftImages(0))
        
        infosButtonsContainer = QWidget()
        self.infosButtonsLayout = QStackedLayout(infosButtonsContainer)
        #self.infosButtonsLayout.setContentsMargins(0,0,0,0)
        
        self.processButton = QPushButton('Process')
        self.processButton.clicked.connect(self.processGrid)
        self.processButton.setDisabled(True)
        self.trackButton = QPushButton('Track')
        self.trackButton.clicked.connect(lambda: self.shiftImages(1))
        self.confirmTrackButton = QPushButton('Confirm')
        self.confirmTrackButton.clicked.connect(lambda: self.shiftImages(2))
        
        self.infosButtonsLayout.addWidget(self.processButton)
        self.infosButtonsLayout.addWidget(self.trackButton)
        self.infosButtonsLayout.addWidget(self.confirmTrackButton)
        
        processLayout.addWidget(referenceLbl)
        processLayout.addWidget(self.referenceImg)
        #processLayout.addStretch(1)
        processLayout.addWidget(self.shiftCorrectionBox)
        processLayout.addWidget(infosButtonsContainer)
        processWidget.setLayout(processLayout)
        
        infosLayout.addWidget(labelWidget)
        infosLayout.addWidget(valueWidget)
        infosLayout.addWidget(processWidget)
        infosWidget.setLayout(infosLayout)
        
        
        firstSeparator = QFrame()
        firstSeparator.setFrameShape(QFrame.VLine)
        firstSeparator.setLineWidth(0)
        secondSeparator = QFrame()
        secondSeparator.setFrameShape(QFrame.VLine)
        secondSeparator.setLineWidth(0)

        horizontalLayout.addStretch(1)
        horizontalLayout.addWidget(self.autoWidget)
        horizontalLayout.addWidget(firstSeparator)
        horizontalLayout.addWidget(self.centerToolWidget)
        horizontalLayout.addWidget(secondSeparator)
        horizontalLayout.addWidget(infosWidget)
        horizontalLayout.addStretch(1)
        
        self.setLayout(horizontalLayout)
    
    
    def prepareTools(self, imageFileList): #initialize the main element boundaries and values
        
        self.nbImagesToProcess = len(imageFileList)
        self.totalImagesValue.setText(str(self.nbImagesToProcess))
        self.totalImagesValue.enterEvent = lambda x: self.totalImagesValue.setText('ClickToChange')
        self.totalImagesValue.leaveEvent = lambda x: self.totalImagesValue.setText(str(self.nbImagesToProcess))
        self.totalImagesValue.mousePressEvent = lambda x: self.changeProcessImages(len(imageFileList))
        
        self.totalMarkersValue.setText(str(0))
        self.corrsizeValue.setRange(5,100)
        self.corrsizeValue.setValue(int(self.parentWidget.parentWindow.profileData['CorrSize'][self.parentWidget.parentWindow.currentProfile]))
        self.currentImageValue.setRange(1,self.nbImagesToProcess)
        self.sizeSlider.setRange(1,10000)
        self.sizeSlider.setValue(500)
        self.rangeSlider.setRange(0,255)
        self.rangeSlider.setValue(127)
        self.nbMarkersX.setRange(2,500)
        self.nbMarkersY.setRange(2,500)
        self.nbMarkersX.setValue(5)
        self.nbMarkersY.setValue(5)
        self.buttonToClick = [self.autoButton, self.rectangleSelection, self.ellipseSelection, self.selectManualButton,  self.addManualButton,  self.removeManualButton]
        
    def changeProcessImages(self, maxImg):
        
        newNb, ok = QInputDialog.getInt(self, 'Change last image number', 'Process until image..', value=self.nbImagesToProcess, minValue=2, maxValue=maxImg)
        if ok:
            self.nbImagesToProcess = newNb
            self.totalImagesValue.setText(str(newNb))
            self.currentImageValue.setRange(1,self.nbImagesToProcess)
        
    def buttonClicked(self, buttonClicked): #when one of the tool button to create a specific grid is clicked, put it in down position and release the others
        
        self.autoSelect(buttonClicked)
        for button in self.buttonToClick:
            if button <> buttonClicked:
                button.setChecked(False)
            else:
                button.setDown(True)
                
    def autoSelect(self, buttonClicked): #activate or deactivate the auto-selection area elements when the user click on the Auto Selection button
        
        if self.autoButton.isChecked() == False and buttonClicked == self.autoButton:
            self.addGridButton.setEnabled(True)
            self.sizeWidget.setEnabled(True)
            self.rangeWidget.setEnabled(True)
            self.elementsWidget.setEnabled(True)
        else:
            self.addGridButton.setDisabled(True)
            self.sizeWidget.setDisabled(True)
            self.rangeWidget.setDisabled(True)
            self.elementsWidget.setDisabled(True)
        self.parentWidget.plotImage()
        
    def imageDeleted(self): #when the user click the checkbox to activate or deactive an image
    
        currentImage = self.currentImageValue.value()-1
        if self.imageActiveBox.isChecked():
            self.parentWidget.imageActiveList[currentImage] = 1
        else:
            self.parentWidget.imageActiveList[currentImage] = 0
            
        self.imageChanged()
            
    def imageChanged(self): #every time the image is changed, show the shift correction displacement and plot the image
        
        currentImage = self.currentImageValue.value()-1
        if self.shiftCorrectionBox.isChecked() and self.largeDisp is not None:
            self.shiftCorrectionWidget.setEnabled(True)
            self.shiftCorrX.setText("{0:.2f}".format(self.largeDisp[currentImage][0]))
            self.shiftCorrY.setText("{0:.2f}".format(self.largeDisp[currentImage][1]))
        else:
            self.shiftCorrectionWidget.setDisabled(True)
        self.parentWidget.plotImage()
                
    def shiftImages(self, track): #manage widget on every steps of the shift correction calculation
        
        if track == 0:
            self.infosButtonsLayout.setCurrentIndex(0)
            if self.shiftCorrectionBox.isChecked() and self.largeDisp is None:
                self.processButton.setDisabled(True)
                self.currentImageValue.setDisabled(True)
                self.trackButton.setEnabled(True)
                self.trackButton.setText('Track')
                self.currentImageValue.setValue(1)
                self.buttonClicked(0)
                self.autoWidget.setDisabled(True)
                self.centerToolWidget.setDisabled(True)
                self.parentWidget.filterToolWidget.setDisabled(True)
            else:
                self.autoWidget.setEnabled(True)
                self.parentWidget.filterToolWidget.setEnabled(True)
                self.centerToolWidget.setEnabled(True)
                self.currentImageValue.setEnabled(True)
                self.shiftCorrectionWidget.setDisabled(True)
                self.parentWidget.plotImage()
                self.largeDisp = None
        elif track == 1: #start a thread an do the calculation                    
            shiftThread = self.parentWidget.parentWindow.createThread([self.parentWidget.parentWindow.filePath, self.parentWidget.imageFileList[0:self.nbImagesToProcess], self.parentWidget.imageActiveList, [self.parentWidget.x0, self.parentWidget.y0, self.parentWidget.x0+self.parentWidget.width, self.parentWidget.y0+self.parentWidget.height], self.parentWidget.filterToolWidget.appliedFiltersList], newProcessCorrelations.shiftDetection, signal=1)
            shiftThread.signal.threadSignal.connect(self.processingShiftCorrection)
            shiftThread.start()
            self.trackButton.setDisabled(True)
            #self.infosButtonsLayout.setCurrentIndex(2)
        elif track == 2:
            self.infosButtonsLayout.setCurrentIndex(0)
            self.autoWidget.setEnabled(True)
            self.centerToolWidget.setEnabled(True)
            self.currentImageValue.setEnabled(True)
            self.parentWidget.filterToolWidget.setEnabled(True)
            self.currentImageValue.setValue(1)
            self.parentWidget.plotImage()
            
    def processingShiftCorrection(self, status): #Receiving the signal data, return infos to the user and save the shift values in the largeDisp variable
        
        [percent, image, shiftX, shiftY] = status
        currentTime = time.time()
        if percent < 100:
            if currentTime > self.lastTime + 1:
                self.currentImageValue.setValue(image)
                self.lastTime = currentTime
                rectCornerX = self.parentWidget.x0+shiftX
                rectCornerY = self.parentWidget.y0+shiftY
                rect = matplotlib.figure.Rectangle((rectCornerX, rectCornerY), self.parentWidget.width, self.parentWidget.height, facecolor='None', edgecolor='green', linewidth=2.5)
                self.parentWidget.figureDisplayWidget.imagePlot.add_patch(rect)
                self.parentWidget.figureDisplayWidget.draw_idle()
            self.trackButton.setText(str(percent)+'%')
        else:
            self.largeDisp = shiftX
            self.infosButtonsLayout.setCurrentIndex(2)
    
    def changeShift(self): #when an user want to manually correct the shift on an image
        
        currentValue = "{0:.2f}".format(float(self.shiftCorrX.text()))+','+"{0:.2f}".format(float(self.shiftCorrY.text()))
        currentImage = self.currentImageValue.value()-1
        value, ok = QInputDialog.getText(self, "Shift Correction", "Set new shift:", QLineEdit.Normal, currentValue)
        if ok:
            vLim = value.split(',')
            if len(vLim) == 2 or vLim[0] is not None or vLim[1] is not None:
                self.largeDisp[currentImage][0] = float(vLim[0])
                self.largeDisp[currentImage][1] = float(vLim[1])
                self.imageChanged()
            else:
                self.parentWidget.parentWindow.devWindow.addInfo('Shift value error. Format : xShift,yShift', statusBar=self.parentWidget.parentWindow.statusBar())
    
    def processGrid(self): #when the process button is clicked, prepare the data, save the grid files and start the correlation process
        
        baseMode = self.referenceImg.currentIndex() # Image reference : 0 Previous / 1 First / 2 Shifted  
        
        floatStep = 0 
        if baseMode == 2: #if floating image reference selected, ask for the step
            intNumber, ok = QInputDialog.getInt(self, "Image Reference Shift Step", "Enter the desired step for image reference:", value=10, minValue=2, maxValue=int(self.totalImagesValue.text()))
            if ok and intNumber:
                floatStep = intNumber
            else:
                return
        
        self.parentWidget.topWidgetStackedLayout.setCurrentIndex(1) #hide the toolWidget and show the progressBar layout
        
        
        gridX = np.array([])
        gridY = np.array([])
        entityX = np.array([])
        entityY = np.array([])
        nb = 0
        
        for element in self.parentWidget.markerInstances:
            gridX = np.hstack((gridX, element[0]))
            gridY = np.hstack((gridY, element[1]))
            entityX = np.hstack((entityX, nb*np.ones_like(element[0], dtype=np.int)))
            entityY = np.hstack((entityY, nb*np.ones_like(element[0], dtype=np.int)))
            nb += 1
            
        gridX = np.transpose(np.vstack((gridX, entityX)))
        gridY = np.transpose(np.vstack((gridY, entityY)))
        #saving gridx and gridy files
        np.savetxt(self.parentWidget.parentWindow.fileDataPath+'/gridx.dat', gridX, fmt='%6f %1d')
        np.savetxt(self.parentWidget.parentWindow.fileDataPath+'/gridy.dat', gridY, fmt='%6f %1d')
        
        #Launch Process
        calculatingThread = self.parentWidget.parentWindow.createThread([self.parentWidget.imageFileList[0:self.nbImagesToProcess], gridX[:,0], gridY[:,0], self.corrsizeValue.value(), baseMode, floatStep, self.parentWidget, self.parentWidget.parentWindow, self.largeDisp, self.parentWidget.filterToolWidget.appliedFiltersList], newProcessCorrelations.prepareCorrelations, signal=1)
        calculatingThread.signal.threadSignal.connect(lambda: StrainAnalysis.analyseResult(self.parentWidget.parentWindow, self.parentWidget.parentWindow))
        calculatingThread.start()
        
        self.parentWidget.mainBottomLayout.removeWidget(self.parentWidget.filterToolWidget)
        self.parentWidget.filterToolWidget.deleteLater()
        self.parentWidget.filterToolWidget = None
        


class matplotlibWidget(FigureCanvas):  #widget to plot image and points inside the dialog and not on a separate window
    
    def __init__(self):
        super(matplotlibWidget,self).__init__(Figure())
        self.figure = Figure()
        self.figure.set_facecolor('none')
        self.canvas = FigureCanvas(self.figure)
        self.imagePlot = self.figure.add_subplot(111)
        self.figure.tight_layout(pad=0)
        self.figure.set_size_inches((20,20)) #high values to allow the image to use as much space as available in the window

