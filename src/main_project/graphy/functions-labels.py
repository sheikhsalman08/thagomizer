import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib import gridspec
from matplotlib.patches import Rectangle
from matplotlib import rc
import matplotlib.patches as mpatches
import subprocess
from operator import itemgetter
import itertools
import sys
import os
import spectra
from io import StringIO

from django.contrib.staticfiles.storage import staticfiles_storage
import main_project.graphy.clip_tools as ct
from django.conf import settings
from io import BytesIO
import pysam
from datascience import *




path_to_static = settings.PATH_TO_STATIC + '/graphy_static/'
file_refseq = path_to_static + "Genome_Data/refseq_names.txt"

from IPython.display import Markdown, display
def printmd(string):
    display(Markdown(string))
    

def graphRefseq(genome_interest,
                refseqid,
                xlim=False,
                strand=False,
                file_refseq=file_refseq,
                ylocation=0,
                LeftToRight=False):
    ''' 
    Generates graph for refseq track. Requires a refseq file (including exon information)
    Can only graph a single transcript at the moment. 
    
    Parameters
    -------
    xlim: [start,stop]
        defines the region to graph 
    strand: "+","-" or False
        set strand to add <<<< or >>>> directional marks
    ylocation: Int or False
        change height of track (not used much)
    '''

    # If there is no gene to be found, return
    if refseqid=="None":
        plt.plot()
        return
    

    ## First Setup the plot
    
    yvals = [ylocation,ylocation]
    if not refseqid=="None":
        hg19reftrack_file = path_to_static+'Genome_Data/hg38.txt'
        if genome_interest == "hg19":
            refdb = pd.read_table(hg19reftrack_file,delimiter="\t",index_col=0,dtype="str")
        if genome_interest == "mm10":
            refdb = pd.read_table(file_refseq,delimiter="\t",index_col=0,dtype="str")
        gene = refdb.loc[str(refseqid)]
        txStart = int(gene.txStart)
        txEnd = int(gene.txEnd)
        wholeLength = map(int,[gene.txStart,gene.txEnd])
        thickStart = int(gene.cdsStart)
        thickEnd = int(gene.cdsEnd)
        starts = map(int,gene.exonStarts.split(",")[:-1])
        stops = map(int,gene.exonEnds.split(",")[:-1])



    


    # Otherwise, lookup the gene and start annotating



    events = [[txStart,"txStart"],[txEnd,"txEnd"],[thickStart,"thickStart"],[thickEnd,"thickEnd"]]
    events = events + [[i,"start"] for i in starts]
    events = events + [[i,"stop"] for i in stops]
    events = sorted(events,key=itemgetter(0))


###### FUTURE CODE: Want to be able to change direction of plot
#     if invert:
#         print events
#         invertdict = {'start':'stop','stop':'start','txStart':'txEnd','txEnd':'txStart','thickEnd':'thickStart','thickStart':'thickEnd'}
#         events = sorted(events,key=itemgetter(0), reverse=True)
#         for n,e in enumerate(events):
#             events[n][1] = invertdict[events[n][1]]
#         print events
        
    
    pen_size = "thin" # can be "thick"
    pen_on = True
    memorylocation = events[0][0]
    start = memorylocation
    bars = [[pen_size,start,0]]
    for location,event in events[1:]:
        if location == memorylocation:
            continue
        if event == "stop":
            if pen_on:
                pen_on = False
                bars[-1][-1] = location
                continue
        if event == "thickStart":
            pen_size = "thick"
            if pen_on:  #if already writing thinline
                bars[-1][-1] = location
                bars.append([pen_size,location,0])
                continue
            else:  #start writing
                pen_on = True
                bars.append([pen_size,location,0])
        if event == "thickEnd":
            pen_size = "thin"
            if pen_on:
                bars[-1][-1] = location
                bars.append([pen_size,location,0])
                continue
            else:  #start writing
                pen_on = False
                bars.append([pen_size,location,0])
        if event == "start":
            if pen_on:
                continue
            pen_on = True
            bars.append([pen_size,location,0])     
    thin_bars = [i[1:] for i in bars if i[0]=="thin"]
    thick_bars = [i[1:] for i in bars if i[0]=="thick"]

    plt.plot(list(wholeLength), yvals,
         "--",
         color="blue",
        )

    for u in thin_bars:
        plt.plot(u,yvals,linewidth=6,color="b",solid_capstyle="butt")
    for e in thick_bars:
        plt.plot(e,yvals,linewidth=20,color="b",solid_capstyle="butt")
    
    if strand:
        if (strand == "+"):
            mark = ">"
        elif strand == "-":
            if LeftToRight:
                mark = ">"
            else:
                mark = "<"
        else:
            raise KeyError
        if xlim:
            plt.xlim(xlim)
            framesize = xlim[1]-xlim[0]
            dashedtraingleline = np.arange(xlim[0],xlim[1],(framesize/10))
        else:
            framesize = wholeLength[1]-wholeLength[0]
            dashedtraingleline = np.arange(wholeLength[0],wholeLength[1],(framesize/10))
        plt.plot(dashedtraingleline,[ylocation]*len(dashedtraingleline),
                 mark,
                 markersize = 4,
                 markeredgecolor="white",
                 color="white",
                )


#     cur_axes = plt.gca()
#     cur_axes.axes.get_xaxis().set_visible(True)
#     cur_axes.axes.get_yaxis().set_visible(False)



def graph_bed_df(genome_interest,bedfile,bedtype,name,chrom,start,stop,strand,stagger = False):
    '''
        Graphs region tracks across a defined region
        
        Parameters
        ----------
        bedfile: File (bed formatted)
        bedtype: string
        Based on kind of format of bed:
        targetscan: "chrom","start","stop","miRNA","score","s2","st2","color"
        custom: "chrom","start","stop","miRNA","zero","strand","geneid","extra"
        bed: "chrom","start","stop","geneid","zero","strand"
        name: str
        chrom: str
        start: int
        stop: int
        strand: int
        stagger: Bool
        Set true if you have a lot of overlapping regions and want them separated.
        
        '''
    
    if bedtype=="targetscan":
        if genome_interest=="hg19":
            bedfile = path_to_static + "Genome_Data/TargetScanHg38.bed"
        beddb = pd.read_table(bedfile, header=None)
        if len(beddb.columns==9):
            beddb.columns=["chrom","start","stop","miRNA","score","strand","start2","stop2","color"]
        else:
            beddb = beddb[0,1,2,3]
            beddb.columns = ["chrom","start","stop","miRNA"]
        beddb_chrom = beddb[beddb.chrom==chrom]
        beddb_local = beddb_chrom[[(beddb_chrom.loc[i].start > start) and (beddb_chrom.loc[i].stop < stop) for i in beddb_chrom.index ]]
        if name == "Targetscan":
            beddb_regions = beddb_local
        else:
            beddb_regions = beddb_local[beddb_local.miRNA==name]
        target_scan = pd.DataFrame({'name':list(beddb_regions.miRNA), 'start':list([i - start for i in beddb_regions.start]), 'stop':list([i - start for i in beddb_regions.stop])})
        ### Line that controls the coordinate system of the TargetScan labels
        return target_scan

def graph_bed(genome_interest,bedfile,bedtype,name,chrom,start,stop,strand,stagger = False):
    ''' 
    Graphs region tracks across a defined region

    Parameters
    ----------
    bedfile: File (bed formatted)
    bedtype: string
        Based on kind of format of bed:
        targetscan: "chrom","start","stop","miRNA","score","s2","st2","color"
        custom: "chrom","start","stop","miRNA","zero","strand","geneid","extra"
        bed: "chrom","start","stop","geneid","zero","strand"
    name: str
    chrom: str
    start: int
    stop: int
    strand: int
    stagger: Bool
        Set true if you have a lot of overlapping regions and want them separated.

    '''

    if bedtype=="targetscan":
        if genome_interest=="hg19":
            bedfile = path_to_static + "Genome_Data/TargetScanHg38.bed"
        beddb = pd.read_table(bedfile, header=None)
        if len(beddb.columns==9):
            beddb.columns=["chrom","start","stop","miRNA","score","strand","start2","stop2","color"]
        else:
            beddb = beddb[0,1,2,3]
            beddb.columns = ["chrom","start","stop","miRNA"]
        beddb_chrom = beddb[beddb.chrom==chrom]
        beddb_local = beddb_chrom[[(beddb_chrom.loc[i].start > start) and (beddb_chrom.loc[i].stop < stop) for i in beddb_chrom.index ]]
        # Check to see if we care about a single miRNA family or all of them.
        if name == "Targetscan":
            beddb_regions = beddb_local
        else:
            beddb_regions = beddb_local[beddb_local.miRNA==name]
        labels = beddb_regions.miRNA
    if bedtype=="custom":
        beddb = pd.read_table(bedfile,names=["chrom","start","stop","miRNA","zero","strand","geneid","extra"])
        beddb_chrom = beddb[beddb.chrom==chrom]
        beddb_local = beddb_chrom[[(beddb_chrom.loc[i].start > start) and (beddb_chrom.loc[i].stop < stop) for i in beddb_chrom.index ]]
        beddb_regions = beddb_local
        labels = beddb_regions.miRNA
    if bedtype=="bed":
        beddb = pd.read_table(bedfile, header=None,names =["chrom","start","stop","geneid","zero","strand"],usecols=[0,1,2,3,4,5])
        beddb_chrom = beddb[beddb.chrom==chrom]
        beddb_chrom = beddb[beddb.strand==strand]
        beddb_local = beddb_chrom[[(beddb_chrom.loc[i].start > start) and (beddb_chrom.loc[i].stop < stop) for i in beddb_chrom.index ]]
        beddb_regions = beddb_local
        labels = beddb_regions.geneid
    regions = [[beddb_regions.loc[i].start,beddb_regions.loc[i].stop] for i in beddb_regions.index]
    regions = sorted(regions,key=itemgetter(0))
    if stagger:
        yvals = [[0,0],[1,1]]*int(len(regions)/2) + ([[0,0]]*int(len(regions)%2))
        linewidth= 5
    else:
        yvals = [[0,0]] * len(regions)
        linewidth= 10
    for n,m in enumerate(regions):
        plt.plot(m,yvals[n],linewidth=linewidth,color="#092A59",solid_capstyle="butt")
    return regions,labels


        
def graph_wig(wig_df,name,chrom,start,stop):
    '''
    Graphs a bigwig file across a defined region
    '''
    wigdf_chrom = wig_df[wig_df.chrom==chrom]
    myrange = range(start,stop)
    depths = pd.DataFrame(index= myrange,columns=["expression"])
    expression = 0
    for n in myrange:
        try:
            expression = wigdf_chrom.loc[wigdf_chrom.start==float(n)].expression
            depths.loc[n,"expression"] = expression.max()
        except IOError:
            depths.loc[n,"expression"] = expression.max()
    return depths

def get_gene_id(chrom,start,stop,strand,bd,choice=0):
    '''
    Return geneIDs in a given region. Retuns string (choice = int) or list (choice = all)
    Requires a BetweenDict generated with clip_tools.BetweenDict

    Parameters
    ---------
    chrom:str
    start: int
    stop: int
    strand: int
    bd: BetweenDict object
        Generated from clip_tools.BetweenDict(bedfile with geneID locations)
    choice: int or "all"
        returns either the nth geneid found in the defined region or
        if "all" is defined, returns a list of all geneids found.
    '''

    myrange = range(start,stop)
    # Figure out the gene name at that location
    # uses the between dict
    geneids =  bd.lookup(chrom,strand,start,stop)
    if choice=='all':
        return geneids
    if len(geneids) == 1:
        geneid = list(geneids)[choice]
        print("Found: %s" % geneid)
    elif len(geneids) > 1:
        geneids = list(geneids)
        print("Found multiple genes: %s" % geneids)
        geneid = geneids[choice]
        print("Picking %s. Set choice=<int> to choose another\n" % geneid)
    else:
        geneid = ""
        print("No gene found")
    return geneid


def get_refseq_id(file_refseq,geneid, choice = 0):
    '''
    Get refseqIDs for a given geneid. If there are multiple, 
    you will have to chose one: choice=n or all choice = 'all'
    

    Parameters
    __________
    file_refseq: file
        refseq file with geneid info and refseqids. 
        formatted: 
        [name    chrom   strand  txStart txEnd   cdsStart    cdsEnd  exonCount   exonStarts  exonEnds    score   name2]
        In this case, name is the RefSeqID and the name2 is the GeneID
    choice: int or "all"
        returns either the nth geneid found in the defined region or
        if "all" is defined, returns a list of all geneids found.
    '''
    if not geneid: return None
    refdb = pd.read_table(file_refseq,delimiter="\t",index_col=0)
    failed = False
    refdb_gene = refdb[refdb.name2 == geneid]
    if choice=='all':
        return refdb_gene.index.format()
    if refdb_gene.chrom.count() > 1:
        failed = True
    if failed == False:
        refseqid = refdb_gene.index.format()[0]
        print("RefseqID is %s" % refseqid)
    else:
        print("Found multiple refseq entries for %s :" % geneid)
        choices = refdb_gene.index.format()
        print(choices)
        refseqid = choices[choice]
        print("Picking %s. Set choice=<int> to choose another\n" % refseqid)
    return refseqid


def get_depth_tracks(df_list,track_names,chrom,start,stop):
    # Populate get the depths for each of the tracks at the given locations
    # Returns depths in a dataframe
    myrange = range(start,stop)
    depths = pd.DataFrame(index= myrange,columns=track_names)

    for track in track_names:
        dfc = df_list[strand][track].loc[chrom].copy()
        for n in myrange:
            try:
                depths.loc[n,track] = dfc.loc[(dfc.start==n)].depth[chrom]
            except KeyError:
                depths.loc[n,track] = 0
    return depths


def get_wig_data(bigwigfiles,wignames,chrom,start,stop):
    wig_df_list = {}
    for n,wig in enumerate(bigwigfiles):
        subprocess.check_output(["bigWigToBedGraph",
                             wig,
                             "temp.temp",
                             "-chrom=%s" %chrom,
                             "-start=%s" % start,
                             "-end=%s" % stop
                            ])
        wig_df = pd.read_table("temp.temp",
                               names =["chrom","start","stop","expression"]) 
        wig_df_list[wignames[n]] = wig_df
    return wig_df_list


def get_depth_data(track_files,track_names,chrom,start,stop,strand,track_type):
    mydepths = pd.DataFrame([0]*(stop-start+1),index=range(start,stop+1),columns=["depth"])
    col_names = [element.split("/")[1] for element in track_names]
    depth_list = pd.DataFrame(0,index=range(start,stop),columns=col_names)
    path_to_static = settings.PATH_TO_STATIC + '/graphy_static/Data/'

    for n,track_file in enumerate(track_files):

        bamfile = pysam.AlignmentFile(path_to_static+track_names[n], index_filename=path_to_static+track_names[n] + '.bai')
        depths_data = bamfile.count_coverage(chrom,start, stop)
        depths_data = [a + b + c + d for a, b, c, d in zip(depths_data[0].tolist(), depths_data[1].tolist(), depths_data[2].tolist(), depths_data[3].tolist())]
        depth_list[col_names[n]] = depths_data 
    return depth_list




def clamp(val, minimum=0, maximum=255):
    if val < minimum:
        return minimum
    if val > maximum:
        return maximum
    return val

def darken(hexstr, scalefactor):
    """
    Scales a hex string by ``scalefactor``. Returns scaled hex string.

    To darken the color, use a float value between 0 and 1.
    To brighten the color, use a float value greater than 1.

    >>> colorscale("#DF3C3C", .5)
    #6F1E1E
    >>> colorscale("#52D24F", 1.6)
    #83FF7E
    >>> colorscale("#4F75D2", 1)
    #4F75D2

    from http://thadeusb.com/weblog/2010/10/10/python_scale_hex_color
    """

    hexstr = hexstr.strip('#')

    if scalefactor < 0 or len(hexstr) != 6:
        return hexstr

    r, g, b = int(hexstr[:2], 16), int(hexstr[2:4], 16), int(hexstr[4:], 16)

    r = clamp(r * scalefactor)
    g = clamp(g * scalefactor)
    b = clamp(b * scalefactor)

    return "#%02x%02x%02x" % (r, g, b)




def plot(figwidth,figheight,refseqtrack,LeftToRight,strand,depths,
       colors,shade,limits,bedtrack,start,stop,staggerbed,bigwignames,
        wig_df_list,shade_by_bed,output_folder,geneid,outputsuffix,outputformat,dpi,track_names,axis_off,
       legend,staticaxes,bedfile,bedtype,name,chrom,refseqid,annotate_bed,fontsize):
    genome_interest = track_names[0].split('/')[0]
    ###### RUN TO PLOT! ######
    track_names = [element.split("/")[1] for element in track_names]

    printmd("Figure will be saved as: %s%s%s.%s"% (output_folder,geneid,outputsuffix,outputformat))
    
    # DON'T MODIFY
    # Note: Need to clean up
    tracks_to_use = range(len(track_names))
    wigtracks_to_use = range(len(bigwignames))
    seqtracks = len(tracks_to_use)
    bedtracks = int(bedtrack)
    wigtracks = len(wigtracks_to_use)
    num_of_tracks = len(tracks_to_use)+int(bedtrack)+len(wigtracks_to_use)+refseqtrack
    height_ratios = ([3]*seqtracks + ([0.4] * bedtracks) + [1] * wigtracks + [1] * refseqtrack)
    if figwidth == 0:
        figwidth = (stop-start)/110
    if limits=='default':
        limits=[start,stop]

    myfont = {'size': fontsize}
    rc('font', **myfont)

    # Initialize Figure
    fig,ax = plt.subplots(1)
    fig.set_figwidth(figwidth)
    fig.set_figheight(figheight)

    gs = gridspec.GridSpec(seqtracks+bedtracks+wigtracks+refseqtrack, 1, height_ratios=height_ratios)
    plotnumber = iter(range(len(height_ratios)))

    # check invert
    invert=False
    if LeftToRight and strand == "-":
        invert=True       

    cur_axes = plt.gca()



    ymax = max(depths.max())
    # Build RNAseq Tracks
    cur_axes_rna = []
    for n in tracks_to_use:
        color = next(colors)
        plt.subplot(gs[next(plotnumber)])
        plt.plot(depths.loc[:,track_names[n]],color=color,linewidth=1)
        plt.fill_between(depths.index,depths.loc[:,track_names[n]].tolist(),color=next(shade),edgecolor='none')
        plt.xlim(limits)
        cur_axes_rna.append(plt.gca())
        cur_axes_rna[n].axes.get_xaxis().set_visible(False)
        cur_axes_rna[n].axes.get_yaxis().set_ticks(cur_axes_rna[n].get_ylim())
        if axis_off:
            cur_axes_rna[n].axes.axis("off")
        if invert:  
            cur_axes_rna[n].invert_xaxis()
        plt.tick_params(labelsize=fontsize)
        if legend:
            red_patch = mpatches.Patch(color=color, label=track_names[n])
            plt.legend(handles=[red_patch],fontsize=fontsize)
        if not staticaxes:
            plt.ylim([0,ymax])

    # Build Bedtracks
    if bedtrack:
        plt.subplot(gs[next(plotnumber)])
        bedregions,bedlabels =graph_bed(genome_interest,bedfile,bedtype,name,chrom,start,stop,strand,stagger=staggerbed)
        cur_axes = plt.gca()
        cur_axes.axes.get_xaxis().set_visible(False)
        cur_axes.axes.get_yaxis().set_ticks([])
        if axis_off: 
            cur_axes.axes.axis("off")
        if invert:
            cur_axes.invert_xaxis()
        plt.ylabel(name,rotation=0,horizontalalignment="right",verticalalignment="center")
        plt.xlim(limits)
        if staggerbed:
            plt.ylim([-1,2])

    # Build Bigwig Tracks
    if len(wigtracks_to_use)>0:
        for n in wigtracks_to_use:
            plt.subplot(gs[next(plotnumber)])
            color = next(colors)
            wigdepths = graph_wig(wig_df_list[bigwignames[n]],name,chrom,start,stop)
            cur_axes = plt.gca()
            cur_axes.axes.get_xaxis().set_visible(False)
            cur_axes.axes.get_yaxis().set_ticks([])
            if axis_off: 
                cur_axes.axes.axis("off")
            if invert:
                cur_axes.invert_xaxis()
            plt.fill_between(wigdepths.index, wigdepths["expression"].tolist(),color=color)
            plt.ylabel(bigwignames[n],rotation=0,horizontalalignment="right",verticalalignment="center")
            # To get relative ylim.. has weird values.
            wig_ylim = [wig_df_list[bigwignames[n]]["expression"].min(),wig_df_list[bigwignames[n]]["expression"].max()]
            # Try again with just -3:3
            wig_ylim = [-3,3]
            plt.ylim(wig_ylim)
            plt.xlim(limits)
        
    # Build Refseq Track
    if refseqtrack:
        plt.subplot(gs[next(plotnumber)])
        graphRefseq(genome_interest,refseqid,
            xlim=limits,
            strand=strand,
            LeftToRight=LeftToRight)
        plt.ylabel(chrom,rotation=0,horizontalalignment="right",verticalalignment="center")
        cur_axes = plt.gca()


    if shade_by_bed:    
        for b in bedregions:
            for n in tracks_to_use:
                # Rectangle(<start(xy)>,<width>,<height>)
                cur_axes_rna[n].add_patch(Rectangle((b[0]-10,0), 20, ymax,
                                                    facecolor="#e2e2e2",
                                                    edgecolor='none',
                                                    alpha=0.7))

    #cur_axes.axes.get_yaxis().set_visible(False)
    cur_axes.axes.get_yaxis().set_ticks([])
    plt.xlabel(geneid)
    plt.ylabel(chrom)
    if axis_off: 
        cur_axes.axes.spines['top'].set_visible(False)
        cur_axes.axes.spines['right'].set_visible(False)
        cur_axes.axes.spines['bottom'].set_visible(False)
        cur_axes.axes.spines['left'].set_visible(False)
        plt.xticks(visible=False)

    if invert:
        cur_axes.invert_xaxis()

    if bedtrack:
            # Remove duplicate bed entries
            bedannotations = zip(bedlabels,bedregions)
            bedannotations = sorted(bedannotations)
            bedannotations = list(i for i,_ in itertools.groupby(bedannotations))
            printmd("======\nRegions\n======")
            for label,x in bedannotations:
                print(label,x)
                if annotate_bed:
                    plt.annotate(
                        label, 
                        xy = (np.mean(x), 0), xytext = (0, -45),
                        textcoords = 'offset points', ha = 'right', va = 'top',
                        rotation = 45,
                        bbox = dict(boxstyle = 'round,pad=0.5', fc = 'yellow', alpha = 0.5),
                        arrowprops = dict(arrowstyle = '-', connectionstyle = 'arc3,rad=0')
                        )
   
    #plt.gca().invert_xaxis()
    #plt.rcParams['axes.facecolor'] = "#dbffe3"
    plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=0.2)

    plt.savefig("%s%s%s.%s"% (output_folder,geneid,outputsuffix,outputformat),
            format=outputformat,
            bbox_inches='tight',
            dpi =dpi)
    
    # Scale the values on the y axis
    #depths.to_csv("out.csv")

    read_data = Table().with_columns("Depths", depths[track_names[0]].tolist())
    def percentile25(arr):
        return percentile(70, arr)
    def bootstrap_estimates(num_replications):
        results = make_array()
        for i in np.arange(num_replications):
            results = np.append(results, percentile25(test.sample().column("difference")))
        
        return results
    read_data = read_data.with_columns("difference", np.append(np.diff(read_data.column("Depths")), 0), "index", np.arange(len(read_data.column("Depths")))+1100)
    mylist = read_data.column("Depths")
    N = 6
    cumsum, moving_aves = [0], []
    for i, x in enumerate(mylist, 1):
        cumsum.append(cumsum[i-1] + x)
        if i>=N:
            moving_ave = (cumsum[i] - cumsum[i-N])/N
            #can do stuff with moving_ave here
            moving_aves.append(moving_ave)
    test = Table().with_columns("ave val", np.append(moving_aves, np.ones(5)-1), "index", read_data.column("index"), "Depths", read_data.column("Depths")).take(np.arange(read_data.num_rows-6))
    test = test.with_columns("difference", np.abs(np.append(np.diff(test.column("ave val")), 0)))
    test = test.with_columns("difference 2", np.abs(np.append(np.diff(test.column("difference")), 0)))
    test = test.take(np.arange(test.num_rows-1))
    stable_regions = test.where("difference", are.below(np.mean(bootstrap_estimates(10000)))).column("index")

    diff_annotations = np.append(1, np.diff(stable_regions))

    combined_table = Table().with_columns("regions", stable_regions,"diff",diff_annotations == np.ones(len(diff_annotations)))
    val = "str "
    arrat = make_array()
    diff_vals = combined_table.column("diff")
    for i in np.arange(combined_table.num_rows):
        if diff_vals.item(i) == True:
            arrat = np.append(arrat, val)
        if diff_vals.item(i) == False:
            arrat = np.append(arrat, "0")
            val = val + str(1)
    combined_table = combined_table.with_columns("Analysis", arrat)#.group("Analysis").show()
    combined_table = combined_table.group("Analysis", min).with_columns("regions max", combined_table.group("Analysis", max).column("regions max")).drop("diff min")
    combined_table = combined_table.take(np.arange(1, combined_table.num_rows))
    def bootstrap_estimates2(num_replications):
        results = make_array()
        for i in np.arange(num_replications):
            results = np.append(results, np.mean(combined_table.sample().column("reads")))

        return results
    array_depths = make_array()
    for i in np.arange(combined_table.num_rows):
        array_depths = np.append(array_depths, np.mean(test.where("index", are.between(combined_table.column("regions min").item(i), combined_table.column("regions max").item(i)+1)).column("ave val")))
    combined_table = combined_table.with_columns("reads", array_depths)
    combined_table = combined_table.where("reads", are.above(percentile(50,bootstrap_estimates2(1000))))
    combined_table = combined_table.with_columns("diff", combined_table.column("regions max") - combined_table.column("regions min"))
    combined_table = combined_table.where("diff", are.above(2))



    start_1 = combined_table.column("regions min")
    stop_1 = combined_table.column("regions max")

    #depths.to_csv("out.csv")
    #for i in range(len(track_names)):
    #max_val = max(depths[track_names[i]])
    #depths[track_names[i]] = [(x/max_val) for x in depths[track_names[i]]]
            
    if bedtype == "targetscan":
        target_scan = graph_bed_df(genome_interest,bedfile,bedtype,name,chrom,start,stop,strand,stagger=staggerbed)
        np_arange_value = len(start_1)
        X_factor = np.append(start_1, [1100 + i for i in target_scan["start"]])
        target_scan["start"] = [1100 + i for i in target_scan["start"]]
        target_scan["stop"] = [1100 + i for i in target_scan["stop"]]
        label_data = pd.DataFrame({'start':np.append(start_1,target_scan["start"]), 'stop':np.append(stop_1, target_scan["stop"]), 'fill':np.append([28 for i in np.arange(np_arange_value)], [12 for i in target_scan["start"]]), "fillOpacity":[0.6 for i in X_factor], 'Text':np.append(["Peak" for i in np.arange(np_arange_value)], target_scan["name"]), 'inside':["true" for i in X_factor], 'rotation':[90 for i in X_factor], 'horizontalCenter':["right" for i in X_factor], 'verticalCenter':["bottom" for i in X_factor]})
        print(label_data)
        depths = depths.to_dict()
        depths['label_data'] = label_data.to_dict()
    else:
        depths = depths.to_dict()
        depths['label_data'] = {}

    
    

    return depths


    





################ for ClipPlot Version ################
def loc_by_refseqid(refseqid):
    
    path_to_static = settings.PATH_TO_STATIC + '/graphy_static/Genome_Data/mm10_refseq_3utr.bed'
    df_refseq_3utr = pd.read_table(path_to_static, names=['chrom','start','stop','name','score','strand'])
    # df_refseq_3utr = pd.read_table("Genome_Data/mm10_refseq_3utr.bed",names=['chrom','start','stop','name','score','strand'])
    df_refseq_3utr.name = ["_".join(x.split("_")[0:2]) for x in df_refseq_3utr.name]
    df_refseq_3utr = df_refseq_3utr.drop_duplicates("name")
    df_refseq_3utr = df_refseq_3utr.set_index("name")
    chrom,start,stop,value,strand = df_refseq_3utr.loc[refseqid]
    return chrom,start,stop,strand

