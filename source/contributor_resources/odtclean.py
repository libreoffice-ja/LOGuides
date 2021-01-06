#!  /usr/bin/python3

# removes direct formating from the content.xml file of an odt document
# by removing the Txxx and OOoDefault styles (if they exist)
# not all Txxx styles are removed

# Author Milos Sramek milos.sramek@soit.sk
# Use as you wish, without warranty

# May 20, 2020: Added more regexp rules 
# May 20, 2020: simplified XML rules

import sys, getopt, os, shutil,re
import zipfile

from lxml import etree
from copy import deepcopy
import sys, getopt, tempfile
import ipdb
#ipdb.set_trace()

def isP(item):
    #if item.tag[-2:]=='}p':
    if item.tag[-2:]=='}p' or item.tag[-2:]=='}h':
        return True
    else:
        return False

def getSpanType(item):
    """
    chect if item is span, but not T-span
    """
    if item.tag.find('span') >= 0:
        for key in list(item.keys()):
            if key.find('style-name') >=0 :
                return item.attrib[key]
    return None

def isSpan(item):
    return item.tag.find('span') >= 0

def isSimpleTag(item):
    """
    a tag is 'simple' if it has no tail or children
    """
    return not (item.tail or len(item.getchildren()))

def mergeSameSpans(tree):
    """
    Merge consecutive spans with the same style-name
    """
    for iitem in tree.xpath('//*'):
        if isP(iitem) and iitem.getchildren():
            if len(iitem.getchildren()) > 1:
                item = deepcopy(iitem)
                elist = list(item)
                prevSpanType = None
                prevItem = elist[0]
                if isSimpleTag(prevItem): prevSpanType = getSpanType(prevItem)
                for el in elist[1:]:
                    if isSpan(el) and (not el.getchildren()) and getSpanType(el) == prevSpanType:
                        if el.text and prevItem.text:
                            prevItem.text = prevItem.text + el.text
                        elif el.text:
                            prevItem.text = el.text
                        # if e.tail exists, assign it to the previous span 
                        # and restart span search
                        if el.tail: 
                            prevItem.tail = el.tail
                            prevSpanType = None
                        item.remove(el)
                    else:
                        prevItem = el
                        prevSpanType = None
                        if isSimpleTag(prevItem): prevSpanType = getSpanType(prevItem)
                iitem.getparent().replace(iitem, item)

def usage():
    global iname, oname
    print("Remove direct character formatting from an odt document")
    print("Usage: ",sys.argv[0]+ " switches ")
    print("\t-h                this usage")
    print("\t-i input_file     a file to clean {%s}"%iname)
    print("\t-o output_file    a cleaned file {%s}"%oname)

def parsecmd():
    global iname, oname
    try:
        opts, Names = getopt.getopt(sys.argv[1:], "hi:o:", [])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err)) # will print something like "option -a not recognized"
        usage(desc)
        sys.exit(2)
    for o, a in opts:
        if o in ("-o"):
            oname = a
        elif o in ("-i"):
            iname = a
        elif o in ("-h"):
            usage()
            sys.exit(0)
        else:
            assert False, "unhandled option"

# process using XML rules
def procXML(fname):
    # parse the 'content.xml' file and clean up
    tree = etree.parse(fname)
    mergeSameSpans(tree)
    tree.write(fname)

# remove tag using regexps
def procRE(fname, tags=[]):
    # parse the 'content.xml' file and clean up
    with open(fname) as ifile:
        text=ifile.read()

    # replace by placeholders to simplify regular expressions later
    text = text.replace("<text:s/>","ASDFGH2323_0")
    text = text.replace("<text:line-break/>","ASDFGH2323_1")

    tags = ['T[0-9]*'] + tags
    for tag in tags:
        # empty T tag
        #text = re.sub(r'<text:span text:style-name="%s"></text:span>'%tag,"",text)

        # <text:span text:style-name="T18">text without tags</text:span>`
        text = re.sub(r'<text:span text:style-name="%s">([^<]*)</text:span>'%tag,r'\1', text)

        # text with one tag
        # <text:span text:style-name="T18"><text:user-defined style:data-style-name="N0" text:name="LibreOffice Version">6.4</text:user-defined></text:span>`
        text = re.sub(r'<text:span text:style-name="%s">(<([^ ]*)[^>]*>[^<]*</\2>)</text:span>'%tag, r"\1",text)

        # text with one selfclosing tag
        #<text:span text:style-name="T9"><text:bookmark-ref text:reference-format="number" text:ref-name="__RefHeading___Toc3630_208225428"/></text:span>
        text = re.sub(r'<text:span text:style-name="%s">(<[^>]*/>)</text:span>'%tag, r"\1",text)

        # display the unchanged T tags
        unchanged=re.findall(r'<text:span text:style-name="%s".*?</text:span>'%tag,text)
        if unchanged:
            print("%s tags not fixed:"%tag)
        for un in unchanged:
            print(un)
            print()

    # revert placeholders
    text = text.replace("ASDFGH2323_1","<text:line-break/>")
    text = text.replace("ASDFGH2323_0","<text:s/>")
    with open(fname, "w") as ifile:
        ifile.write(text)

oname = './ofile.odt'
iname = './ifile.odt'
parsecmd()

if not os.path.isfile(iname):
    print("%s error: file %s does not exist"%(sys.argv[0], iname))
    iname = './ifile.odt'
    usage()
    sys.exit(0)
tmpdir=tempfile.mkdtemp()
verbose=True #

# directory to extract the odt file to
actdir=os.getcwd()
if not os.path.isabs(iname):
    iname = actdir+'/'+iname
if not os.path.isabs(oname):
    oname = actdir+'/'+oname

#extract the document
try:
    with zipfile.ZipFile(iname, "r") as z:
        z.extractall(tmpdir)
except zipfile.BadZipFile as err:
    print("%s error: file %s is not an odt file"%(sys.argv[0], iname))
    iname = './ifile.odt'
    usage()
    sys.exit(0)

# remove output, if exists. Otherwise the zip routine would update it
if os.path.isfile(oname):
    os.remove(oname)

#open the output document - zip file
zf = zipfile.ZipFile(oname, "w")

#ennter the directory with the extracted document
os.chdir(tmpdir)

#List additional tags to remove
#procRE('content.xml', ['LibOStandard', 'Character_20_style'])
procRE('content.xml')
procXML('content.xml')

# save the modified document
for dirname, subdirs, files in os.walk('.'):
    for filename in files:
        zf.write(os.path.join(dirname, filename))
zf.close()

#return back and remove the extracted document
os.chdir(actdir)
shutil.rmtree(tmpdir)
