import matplotlib
import pytools as pt
import numpy as np
import matplotlib.pyplot as plt
import scipy
import os
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.colors import BoundaryNorm,LogNorm,SymLogNorm
from matplotlib.ticker import MaxNLocator
from matplotlib.ticker import LogLocator
import matplotlib.ticker as mtick
import colormaps as cmaps
from matplotlib.cbook import get_sample_data
import plot_run_defaults

# Run TeX typesetting through the full TeX engine instead of python's own mathtext. Allows
# for changing fonts, bold math symbols etc, but may cause trouble on some systems.
matplotlib.rc('text', usetex=True)
matplotlib.rcParams['text.latex.preamble'] = [r'\boldmath']
matplotlib.rcParams['mathtext.fontset'] = 'stix'
matplotlib.rcParams['font.family'] = 'STIXGeneral'
# matplotlib.rcParams['text.dvipnghack'] = 'True' # This hack might fix it on some systems

# Register custom colourmaps
plt.register_cmap(name='viridis', cmap=cmaps.viridis)
plt.register_cmap(name='viridis_r', cmap=matplotlib.colors.ListedColormap(cmaps.viridis.colors[::-1]))
plt.register_cmap(name='plasma', cmap=cmaps.plasma)
plt.register_cmap(name='plasma_r', cmap=matplotlib.colors.ListedColormap(cmaps.plasma.colors[::-1]))
plt.register_cmap(name='inferno', cmap=cmaps.inferno)
plt.register_cmap(name='inferno_r', cmap=matplotlib.colors.ListedColormap(cmaps.inferno.colors[::-1]))
plt.register_cmap(name='magma', cmap=cmaps.magma)
plt.register_cmap(name='magma_r', cmap=matplotlib.colors.ListedColormap(cmaps.magma.colors[::-1]))
# plt.register_cmap(name='cork',cmap=cork_map)
# plt.register_cmap(name='davos_r',cmap=davos_r_map)

# Different style scientific format for colour bar ticks
def fmt(x, pos):
    a, b = '{:.1e}'.format(x).split('e')
    b = int(b)
    return r'${}\times10^{{{}}}$'.format(a, b)

def plot_colormap(filename=None,
                  vlsvobj=None,
                  filedir=None, step=None,
                  outputdir=None,
                  var=None, op=None, title=None,
                  draw=None, usesci=None,
                  symlog=None,
                  boxm=[],boxre=[],colormap=None,
                  run=None,notime=None,wmark=None,
                  notre=None, thick=1.0,
                  vmin=None, vmax=None, lin=None,
                  external=None, extvals=None,
                  expression=None, exprvals=None
                  ):

    ''' Plots a coloured plot with axes and a colour bar.

    :kword filename:    path to .vlsv file to use for input. Assumes a bulk file.
    :kword vlsvobj:     Optionally provide a python vlsvfile object instead
    :kword filedir:     Optionally provide directory where files are located and use step for bulk file name
    :kword step:        output step index, used for constructing output (and possibly input) filename
    :kword outputdir:   path to directory where output files are created (default: $HOME/Plots/)
                        If directory does not exist, it will be created. If the string does not end in a
                        forward slash, the final parti will be used as a perfix for the files.
     
    :kword var:         variable to plot, e.g. rho, rhoBeam, beta, temperature, MA, Mms, va, vms,
                        E, B, V or others. Accepts any variable known by analysator/pytools.
    :kword op:          Operator to apply to variable: None, x, y, or z. Vector variables return either
                        the queried component, or otherwise the magnitude. 

    :kword boxm:        zoom box extents [x0,x1,y0,y1] in metres (default and truncate to: whole simulation box)
    :kword boxre:       zoom box extents [x0,x1,y0,y1] in Earth radii (default and truncate to: whole simulation box)
    :kword colormap:    colour scale for plot, use e.g. jet, viridis, plasma, inferno, magma, nipy_spectral, RdBu
    :kword run:         run identifier, used for some default vmin,vmax values and for constructing output filename
    :kword notime:      flag to suppress plotting simulation time in title
    :kword title:       string to use as title in lieu of map name
    :kword notre:       flag to use metres (if ==1) or kilometres as axis unit
    :kword thick:       line and axis thickness, default=1.0
    :kwird usesci:      Use scientific notation for colorbar ticks? (default: 1)
    :kword vmin,vmax:   min and max values for colour scale and colour bar. If no values are given,
                        min and max values for whole plot (non-zero rho regions only) are used.
    :kword lin:         flag for using linear colour scaling instead of log
    :kword symlog:      use logarithmic scaling, but linear when abs(value) is below the value given to symlog.
                        Allows symmetric quasi-logarithmic plots of e.g. transverse field components.
                        A given of 0 translates to a threshold of max(abs(vmin),abs(vmax)) * 1.e-2.
    :kword wmark:       If set to non-zero, will plot a Vlasiator watermark in the top left corner.
    :kword draw:        Draw image on-screen instead of saving to file (requires x-windowing)
   
    :kword external:    Optional function which receives the image axes in order to do further plotting
    :kword extvals:     Optional array of map names to pass to the external function

    :kword expression:  Optional function which calculates a custom expression to plot. Remember to set
                        vmin and vmax manually.
    :kword exprvals:    Array of map names to pass to the optional expression function (as np.arrays)
                            
    :returns:           Outputs an image to a file or to the screen.

    .. code-block:: python

    # Example usage:
    plot_colormap(filename=fileLocation, var="MA", run="BCQ",
                  colormap='nipy_spectral',step=j, outputdir=outputLocation,
                  lin=1, wmark=1, vmin=2.7, vmax=10, 
                  external=cavitoncontours, extvals=['rho','B','beta'])
    # Where cavitoncontours is an external function which receives the arguments
    #  ax, XmeshXY,YmeshXY, extmaps
    # where extmaps is an array of maps for the requested variables.

    # example (simple) use of expressions:
    def exprMA_cust(exprmaps): #where exprmaps contains va, and the function returns the M_A with a preset velocity
        custombulkspeed=750000. # m/s
        va = exprmaps[0][:,:]
        MA = custombulkspeed/va
        return MA
    plot_colormap(filename=fileLocation, vmin=1 vmax=40,
                  expression=exprMA_cust, extvals=['va'],lin=1)

    '''

    # Verify the location of this watermark image
    watermarkimage=os.path.join(os.path.dirname(__file__), 'logo_color.png')
    # watermarkimage=os.path.expandvars('$HOME/appl_taito/analysator/pyPlot/logo_color.png')
    # watermarkimage='/homeappl/home/marbat/appl_taito/analysator/logo_color.png'

    if outputdir==None:
        outputdir=os.path.expandvars('$HOME/Plots/')
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    # Input file or object
    if filename!=None:
        f=pt.vlsvfile.VlsvReader(filename)
    elif vlsvobj!=None:
        f=vlsvobj
    elif ((filedir!=None) and (step!=None)):
        filename = filedir+'bulk.'+str(step).rjust(7,'0')+'.vlsv'
        f=pt.vlsvfile.VlsvReader(filename)
    else:
        print("Error, needs a .vlsv file name, python object, or directory and step")
        return

    # Scientific notation for colorbar ticks?
    if usesci==None:
        usesci=1
    
    if colormap==None:
        #colormap="plasma"
        #colormap="viridis_r"
        #colormap="inferno"
        #colormap="seismic"
        colormap="plasma_r"
    cmapuse=matplotlib.cm.get_cmap(name=colormap)

    fontsize=8 # Most text
    fontsize2=10 # Time title
    fontsize3=5 # Colour bar ticks

    # Plot title with time
    if notime==None:        
        timeval=f.read_parameter("time")
        if timeval == None:
            timeval=f.read_parameter("t")
            if timeval == None:    
                print "Unknown time format encountered"
                plot_title = ''
        if timeval != None:
            plot_title = "t="+str(np.int(timeval))+' s'
    else:
        plot_title = ''       

    # step, used for file name
    if step!=None:
        stepstr = '_'+str(step).rjust(7,'0')
    else:
        stepstr = ''

    # If run name isn't given, just put "plot" in the output file name
    if run==None:
        run='plot'

    # Verify validity of operator
    opstr=''
    if op!=None:
        if op!='x' and op!='y' and op!='z':
            print("Unknown operator "+op)
            op=None            
        else:
            # For components, always use linear scale, unless symlog is set
            opstr='_'+op
            if symlog==None:
                lin=1

    # Output file name
    if expression!=None:
        varstr=expression.__name__ 
    else:        
        if var==None:
            # If no expression or variable given, defaults to rho
            var='rho'
        varstr=var
    savefigname = outputdir+run+"_map_"+varstr+opstr+stepstr+".png"

    Re = 6.371e+6 # Earth radius in m
    #read in mesh size and cells in ordinary space
    xsize = f.read_parameter("xcells_ini")
    ysize = f.read_parameter("ycells_ini")
    zsize = f.read_parameter("zcells_ini")
    cellids = f.read_variable("CellID")
    xmin = f.read_parameter("xmin")
    xmax = f.read_parameter("xmax")
    ymin = f.read_parameter("ymin")
    ymax = f.read_parameter("ymax")
    zmin = f.read_parameter("zmin")
    zmax = f.read_parameter("zmax")

    # Check if ecliptic or polar run
    if ysize==1:
        simext=[xmin,xmax,zmin,zmax]
        sizes=[xsize,zsize]
    if zsize==1:
        simext=[xmin,xmax,ymin,ymax]
        sizes=[xsize,ysize]

    # Select window to draw
    if len(boxm)==4:
        boxcoords=boxm
    elif len(boxre)==4:
        boxcoords=[i*Re for i in boxre]
    else:
        boxcoords=simext

    # If box extents were provided manually, truncate to simulation extents
    boxcoords[0] = max(boxcoords[0],simext[0])
    boxcoords[1] = min(boxcoords[1],simext[1])
    boxcoords[2] = max(boxcoords[2],simext[2])
    boxcoords[3] = min(boxcoords[3],simext[3])

    # Axes and units (default R_E)
    unitstr = r'$\mathrm{R}_{\mathrm{E}}$'
    unit = Re
    if notre!=None: # Use m or km instead
        if notre==1:
            unit = 1.0
            unitstr = 'm'
        else:
            unit = 1.e3
            unitstr = 'km'

    # Scale data extent and plot box
    simext=[i/unit for i in simext]
    boxcoords=[i/unit for i in boxcoords]

    ##########
    # Read data and calculate required variables
    ##########
    if expression==None:
        if var == 'rho':
            cb_title = r"$n_\mathrm{p} [\mathrm{m}^{-3}]$"
            datamap = f.read_variable("rho")

        elif var == 'rhoBeam':
            cb_title = r"$\rho_{\mathrm{beam}} [\mathrm{m}^{-3}]$"
            datamap = f.read_variable("RhoBackstream")

        elif var == 'beta':
            cb_title = r"$\beta$"
            datamap = f.read_variable("beta")

        elif var == 'temperature':
            cb_title = r"$T$ [K]"
            datamap = f.read_variable("Temperature")

        elif var == 'MA':
            cb_title = r"$\mathrm{M}_\mathrm{A}$"
            Vmag = f.read_variable("v",operator='magnitude')
            va = f.read_variable("va")
            datamap = Vmag/va

        elif var == 'Mms':
            cb_title = r"$\mathrm{M}_\mathrm{ms}$"
            Vmag = f.read_variable("v",operator='magnitude')
            vms = f.read_variable("vms")
            datamap = Vmag/vms

        elif var == 'va':
            cb_title = r"$v_\mathrm{A}$"
            datamap = f.read_variable("va")

        elif var == 'vms':
            cb_title = r"$v_\mathrm{ms}$"
            datamap = f.read_variable("vms")

        elif var == 'B':
            if op==None:
                cb_title = r"$|B|$ [T]"
                datamap = f.read_variable("B",operator='magnitude')
            else:
                cb_title = r"$B_"+op+"$ [T]"
                datamap = f.read_variable("B",operator=op)
                # datamap = datamap*1e+9 # could be used to output nanotesla instead of tesla

        elif var == 'E':
            if op==None:
                cb_title = r"$|E|$ [V/m]"
                datamap = f.read_variable("E",operator='magnitude')
            else:
                cb_title = r"$E_"+op+"$ [V/m]"
                datamap = f.read_variable("E",operator=op)

        elif var == 'V':
            if op==None:
                cb_title = r"$|V|\,[\mathrm{m}\,\mathrm{s}^{-1}]$"
                datamap = f.read_variable("v",operator='magnitude')
            else:
                cb_title = r"$V_"+op+"\,[\mathrm{m}\,\mathrm{s}^{-1}]$"
                datamap = f.read_variable("v",operator=op)
                # datamap = datamap*1e-3 # Plot this as km/s instead of m/s

        else:
            # Pipe all other vars directly to analysator
            if op==None:
                cb_title = var
                datamap = f.read_variable(var)
                # If value was vector value, take magnitude
                if np.ndim(datamap) != 1:
                    cb_title = r"$|"+var+"|$"
                    datamap = np.sum(np.asarray(datamap)**2,axis=-1)**(0.5)
            else:
                cb_title = r+""+var+"$_"+op+"$"
                datamap = f.read_variable(var,operator=op)            
            
        if np.ndim(datamap)!=1:
            print("Error reading variable "+var+"! Exiting.")
            return -1

        # Reshape data to an ordered 2D array that can be plotted
        if np.ndim(datamap) != 2:
            datamap = datamap[cellids.argsort()].reshape([sizes[1],sizes[0]])

    else:
    # Optional user-defined expression overrides the var
    # Optional external additional plotting routine
        exprmaps=[]
        if exprvals==None:
            print("Error, expression must have some variable maps to work on.")
            return
        else:
            # Gather the required variable maps for the expression function
            for mapval in exprvals:
                exprmap = f.read_variable(mapval)
                if np.ndim(exprmap)==1:
                    exprmap = exprmap[cellids.argsort()].reshape([sizes[1],sizes[0]])
                else:
                    exprmap = exprmap[cellids.argsort()].reshape([sizes[1],sizes[0],len(exprmap[0])])
                exprmaps.append(np.ma.asarray(exprmap))
        datamap = expression(exprmaps)             
        if np.ndim(datamap)!=2:
            print("Error calling custom expression "+expression+"! Result was not a 2-dimensional array. Exiting.")
            return -1

    # Load default values
    (vminuse, vmaxuse) = plot_run_defaults.loadrundefaults(run, var, op)

    # If given, override default vmin and vmax values with input keywords
    if vmin!=None:
        vminuse=vmin
    if vmax!=None:
        vmaxuse=vmax

    vminfound=None
    vmaxfound=None
    # If default values not available, take min and max of array
    if vminuse==None or vmaxuse==None:
        # Only use values where rho is positive, i.e. mask out magnetosphere
        rhomap = f.read_variable("rho")
        rhomap = rhomap[cellids.argsort()].reshape([sizes[1],sizes[0]])
        rhoindex = np.where(rhomap > np.finfo(float).eps)
    if vminuse==None:
        vminuse=np.amin(datamap[rhoindex])
        vminfound=1
    if vmaxuse==None:
        vmaxuse=np.amax(datamap[rhoindex])
        vmaxfound=1

    # If vminuse and vmaxuse are extracted from data, different signs, and close to each other, adjust to be symmetric
    # e.g. to plot transverse field components
    if vminfound!=None and vmaxfound!=None:
        if (vminuse*vmaxuse < 0) and (abs(abs(vminuse)-abs(vmaxuse))/abs(vminuse) < 0.4 ) and (abs(abs(vminuse)-abs(vmaxuse))/abs(vmaxuse) < 0.4 ):
            absval = max(abs(vminuse),abs(vmaxuse))
            if vminuse < 0:
                vminuse = -absval
                vmaxuse = absval
            else:
                vminuse = absval
                vmaxuse = -absval

    # Check that lower bound is valid
    if (vminuse <= 0) and (lin==None) and (symlog==None):
        # Assume 5 orders of magnitude is enough?
        print("Vmin value invalid for log scale, defaulting to 1.e-5 of maximum value")
        vminuse = vmaxuse*1.e-5

    # If symlog scaling is set:
    if symlog!=None:
        if symlog>0:
            linthresh = symlog 
        else:
            linthresh = max(abs(vminuse),abs(vmaxuse))*1.e-2

    # Lin or log colour scaling, defaults to log
    if lin==None:
        # Special SymLogNorm case
        if symlog!=None:
            #norm = SymLogNorm(linthresh=linthresh, linscale = 0.3, vmin=vminuse, vmax=vmaxuse, ncolors=cmapuse.N, clip=True)
            norm = SymLogNorm(linthresh=linthresh, linscale = 0.3, vmin=vminuse, vmax=vmaxuse, clip=True)
            maxlog=int(np.ceil(np.log10(vmaxuse)))
            minlog=int(np.ceil(np.log10(-vminuse)))
            logthresh=int(np.floor(np.log10(linthresh)))
            logstep=1
            ticks=([-(10**x) for x in range(logthresh, minlog+1, logstep)][::-1]
                    +[0.0]
                    +[(10**x) for x in range(logthresh, maxlog+1, logstep)] )
        else:
            norm = LogNorm(vmin=vminuse,vmax=vmaxuse)
            ticks = LogLocator(base=10,subs=range(10)) # where to show labels
    else:
        # Linear
        levels = MaxNLocator(nbins=255).tick_values(vminuse,vmaxuse)
        norm = BoundaryNorm(levels, ncolors=cmapuse.N, clip=True)
        ticks = np.linspace(vminuse,vmaxuse,num=7)            

    # Select ploitting back-end based on on-screen plotting or direct to file without requiring x-windowing
    if draw!=None:
        plt.switch_backend('TkAgg')
    else:
        plt.switch_backend('Agg')  

    # Select image shape to match plotted area, at least somewhat.
    # default for square figure is figsize=[4.0,3.15]
    ratio = np.sqrt((boxcoords[3]-boxcoords[2])/(boxcoords[1]-boxcoords[0]))
    figsize = [4.0,3.15*ratio]

    # Create 300 dpi image of suitable size
    fig = plt.figure(figsize=figsize,dpi=300)
    
    # Generates the mesh to map the data to
    [XmeshXY,YmeshXY] = scipy.meshgrid(np.linspace(simext[0],simext[1],num=sizes[0]),np.linspace(simext[2],simext[3],num=sizes[1]))
    fig1 = plt.pcolormesh(XmeshXY,YmeshXY,datamap, cmap=colormap,norm=norm)
    ax1 = plt.gca() # get current axes

    # Title and plot limits
    ax1.set_title(plot_title,fontsize=fontsize2,fontweight='bold')
    plt.xlim([boxcoords[0],boxcoords[1]])
    plt.ylim([boxcoords[2],boxcoords[3]])
    ax1.set_aspect('equal')

    for axis in ['top','bottom','left','right']:
        ax1.spines[axis].set_linewidth(thick)
    ax1.xaxis.set_tick_params(width=thick,length=3)
    ax1.yaxis.set_tick_params(width=thick,length=3)
    #ax1.xaxis.set_tick_params(which='minor',width=3,length=5)
    #ax1.yaxis.set_tick_params(which='minor',width=3,length=5)

    # Limit ticks, slightly according to ratio
    ax1.xaxis.set_major_locator(plt.MaxNLocator(int(7/np.sqrt(ratio))))
    ax1.yaxis.set_major_locator(plt.MaxNLocator(int(7*np.sqrt(ratio))))

    plt.xlabel('X ['+unitstr+']',fontsize=fontsize,weight='black')
    if ysize==1: #Polar
        plt.ylabel('Z ['+unitstr+']',fontsize=fontsize,weight='black')
    else: #Ecliptic
        plt.ylabel('Y ['+unitstr+']',fontsize=fontsize,weight='black')
    plt.xticks(fontsize=fontsize,fontweight='black')
    plt.yticks(fontsize=fontsize,fontweight='black')

    # set axis exponent offset font sizes
    ax1.yaxis.offsetText.set_fontsize(fontsize)
    ax1.xaxis.offsetText.set_fontsize(fontsize)

    # Optional external additional plotting routine overlayed on color plot
    if external!=None:
        extmaps=[]
        if extvals!=None:
            for mapval in extvals:
                extmap = f.read_variable(mapval)
                if np.ndim(extmap)==1:
                    extmap = extmap[cellids.argsort()].reshape([sizes[1],sizes[0]])
                else:
                    extmap = extmap[cellids.argsort()].reshape([sizes[1],sizes[0],len(extmap[0])])
                extmaps.append(extmap)
        extresult=external(ax1, XmeshXY,YmeshXY, extmaps)            

    if title==None:
        if expression!=None:
            cb_title_use = expression.__name__
        else:
            cb_title_use = cb_title
    else:
        cb_title_use = title

    # Colourbar title
    cb_title_locy = 1.0 + 0.05/ratio
    plt.text(1.0, 1.05, cb_title_use, fontsize=fontsize,weight='black', transform=ax1.transAxes)

    # Witchcraft used to place colourbar
    divider = make_axes_locatable(ax1)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    # First draw colorbar
    if usesci==0:        
        cb = plt.colorbar(fig1,ticks=ticks,cax=cax)
    else:
        cb = plt.colorbar(fig1,ticks=ticks,format=mtick.FuncFormatter(fmt),cax=cax)
    cb.ax.tick_params(labelsize=fontsize3)#,width=1.5,length=3)
    cb.outline.set_linewidth(thick)

    # if too many subticks:
    if lin==None and usesci!=0 and symlog==None:
        # Note: if usesci==0, only tick labels at powers of 10 are shown anyway.
        # For non-square pictures, adjust tick count
        nlabels = len(cb.ax.yaxis.get_ticklabels()) / ratio
        if nlabels > 10:
            valids = ['1','2','3','4','5','6','8']
        if nlabels > 19:
            valids = ['1','2','5']
        if nlabels > 28:
            valids = ['1']
        #for label in cb.ax.yaxis.get_ticklabels()[::labelincrement]:
        if nlabels > 10:
            for label in cb.ax.yaxis.get_ticklabels():
                # labels will be in format $x.0\times10^{y}$
                if not label.get_text()[1] in valids:
                    label.set_visible(False)

    # Add Vlasiator watermark
    if wmark!=None:        
        wm = plt.imread(get_sample_data(watermarkimage))
        newax = fig.add_axes([0.01, 0.90, 0.3, 0.08], anchor='NW', zorder=-1)
        newax.imshow(wm)
        newax.axis('off')

    # adjust layout
    plt.tight_layout()

    # Save output or draw on-screen
    if draw==None:
        print(savefigname+"\n")
        plt.savefig(savefigname,dpi=300)
    else:
        plt.draw()
        plt.show()
    plt.close()
    plt.clf()