#!/usr/bin/env python3
#https://github.com/WeblateOrg/weblate/issues/1476

# spellcheck translated messages
#cat ui_sk.csv |tr " " "\n" | tr "/-" "\n"| tr "]" "." |sed -e "s/[.,\"()<*>=:;%?&'{}[]//g"|sed -e "s/[0-9\!\^„“#]//g"|sed -e "s/.*[a-Z][A-Z].*//"|sort|uniq|aspell -l sk list

# edit all by sed
#for i in `find libo_ui-master -name [a-Z]\*.po`; do sed -i -f err-sel.sed $i; done

#find the \x character, which breaks autotranslate
#the character is the space betwee ""
#grep "­" `find libo_ui-master/ -name [^.]\*.po`


import sys, getopt, csv, re, time
import os, shutil, filecmp
from os import path
import ipdb
import json
import polib
from collections import defaultdict
import numpy as np
from difflib import SequenceMatcher


def usage():
    global wsite, csv_import, projects
    proj_abb = [k for k in projects.keys()]
    print()
    print("%s: Transfer extended tooltip string from the LibreOffice help translation files to UI files or vice versa"%sys.argv[0])
    print("Usage: ",sys.argv[0]+ " switches command")
    print("Switches:")
    print("\t-h                  this usage")
    #print("\t-v                 be verbose")
    print("\t-w site             Weblate site URL {taken from the WEBLATE_API_SITE environment variable}")
    print("\t-p project          Abbreviation of Weblate's subproject (slug) %s"%proj_abb)
    print("\t-k key              Weblate account key {taken from the WEBLATE_API_KEY environment variable}")
    print("\t-l lang_code        language code {taken from the WEBLATE_API_LANG environment variable}")
    print("Commands (with their specific switches):")
    print("\tdownload\tDownload translation files for the project specidied by the -p switch")
    print("\t\t-d                redownload translation files")
    print("\tmodified\tList modified files")
    print("\tdifferences\tShow differences in modified files")
    print("\trevert\t\tRevert modified files to the original state")
    print("\tfixchar\t\tfix trailing characters and extra spaces")
    print("\tupload\t\tupload modified files to server")
    print("\ttransfer\ttransfer existing translations of extended tooltips from another project")
    print("\t\t-n project        project to transfer translations from.")
    print("\t\t                  If transferring between 'ui' projects, tranfers are only between messages with identical KeyId.")
    print("\t\t                  If transferring between 'ui' and 'help' project, only tooltips are transferred.")
    print('\tglossary\texport unique messages in csv format to stdout as "source","target". May be used as glossary in OmegaT and maybe elsewhere ')
    print("\t\t-m                max lenght of exported messages {all}")
    print("\t\t                  accelerator characters _ and ~ are removed and newlines replaced by a placeholder")
    print('\texport\t\texport messages in csv format to stdout (with newlines replaced by placeholders)')
    print("\t\t-u                export only untranslated messages")
    print("\t\t-f                export conflicting translations (more than one msgstr for one msgid)")
    print("\t\t-r                export conflicting translations (reversed, more than one msgid for one msgstr)")
    print("\t\t-g                export translations with inconsistent tags")
    print("\t\t-t                export only extended tooltips (<ahelp> in help, 'extended' in entry.msgctxt in ui)")
    print("\t\tswitch modifiers:")
    print("\t\t-i                export only translations with conflicting translation of UI substrings")
    print("\t\t-a                do not abbreviate tags")
    print("\t\t-x lang{,lang}    extra language to add to export as reference (no space after ,)")
    print("\t\t-e                automatically translate substrings found in the 'ui' component")
    print("\t\t-y                verify translation using a translation service")
    #print("\t\t-o                export extended tooltips, if they are translated on the 'other' side")
    print("\timport\t\timport translations from a csv file")
    print("\t\t-c csv_file       csv file to import translations (tab separated)")
    print("\t\t\t\t  Structure: 4 columns, the same content as when exported")
    print("\thelp\t\tThis help")


def parsecmd():
    global wsite, api_key, trans_project, lang, verbose, csv_import, conflicts_only, tooltips_only, conflicts_only_rev, translated_other_side,transfer_from, inconsistent_tags, no_abbreviation, autotranslate, extra_languages, inconsistent_ui_trans, verify_translation, untranslated_only, redownload_downloaded, glossary_max
    try:
        opts, cmds = getopt.getopt(sys.argv[1:], "hvfrtogaeuydw:p:k:l:c:n:x:n:m:", [])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err)) # will print something like "option -a not recognized")
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ("-w"):
            wsite = a
        if o in ("-v"):
            verbose = True
        elif o in ("-p"):
            trans_project = a
        elif o in ("-k"):
            api_key = a
        elif o in ("-l"):
            lang = a
        elif o in ("-c"):
            csv_import = a
        elif o in ("-m"):
            glossary_max = int(a)
        elif o in ("-n"):
            transfer_from = a
        elif o in ("-e"):
            autotranslate = True
        elif o in ("-a"):
            no_abbreviation = True
        elif o in ("-i"):
            inconsistent_ui_trans = True
        elif o in ("-d"):
            redownload_downloaded = True
        elif o in ("-u"):
            untranslated_only = True
        elif o in ("-f"):
            conflicts_only = True
        elif o in ("-r"):
            conflicts_only_rev = True
        elif o in ("-t"):
            tooltips_only = True
        elif o in ("-g"):
            inconsistent_tags = True
        elif o in ("-o"):
            translated_other_side = True
        elif o in ("-y"):
            verify_translation = True
        elif o in ("-x"):
            extra_languages = a.split(",")
            if extra_languages[-1] == "":
                usage()
                sys.exit(0)
            #ipdb.set_trace()
            pass
        elif o in ("-h"):
            usage()
            sys.exit(0)
        else:
            assert False, "unhandled option"
    return cmds

#hidden dot files are used to back up the translation files
def get_dot_name(filename):
    return path.join(path.dirname(filename),"."+path.basename(filename))

def request_get(url):
    global token
    curl_command = f'curl -s -X GET -H "authorization: {token}" {url}'

    response=os.popen(curl_command).read()
    if not response:
        print(f"request_get: no response from server")
    elif "DOCTYPE html" in response:
        respname = "server-error-%s.html"%time.ctime().replace(" ","-")
        print(f"request_get: server problem, repeating the request. Server response saved to %s"%respname)   
        with open(respname, 'w') as f:
            f.write(response)
    elif "Bad Request" in response:
        print(f"request_get: curl commad corrupted (Bad Request)")
    elif "Bad Gateway" in response:
        print(f"request_get: curl commad failed (Bad Gateway)")
    elif "<html>" in response:
        print(f"request_get: curl commad corrupted (HTML response)")
    elif "Server Error" in response:
        print(f"request_get: curl commad failed (Server Error)")
    else:
        try:
            # if json
            response_dir=json.loads(response)
            if 'detail' in response_dir:
                print(f"request_get: Command failed ({response_dir['detail']} {url})")
                return ""
            elif "error" in response_dir:
                    ipdb.set_trace()
                    pass
            return response_dir
        except ValueError as err:
            # if other formate, e. g. po
            return response
    return ""

def upload_file(fpath, furl):
    global token
    curl_command = f'curl -s -X POST -F overwrite=true -F file=@{fpath} -H "authorization: {token}" {furl}/'
    if verbose: print(f"Uploading file {fpath}")
    response=os.popen(curl_command).read()
    if not response:
        print(f"Upload_file: Probably incorrect file path ({fpath})")
        sys.exit(1)
    elif "DOCTYPE html" in response:
        print(f"Upload_file: Probably incorrect url path ({furl})")
        sys.exit(1)
    elif "Bad Request" in response:
        print(f"Upload_file: curl commad corrupted")
        sys.exit(1)
    else:
        response_dir=json.loads(response)
        if 'detail' in response_dir:
            print(f"Upload_file: Command failed ({response_dir['detail']})")
            sys.exit(1)
        else:
            if verbose: print("  Result: %s"%response)

#get subproject slugs (slug: a machine name of a subproject in Weblate)
def download_subproject_file_list(project_name,lang):
    global wsite
    json_path_name = path.join(project_name, lang, 'files.json')
    if os.path.exists(json_path_name):
        return

    #get subproject slugs (slug: a machine name of a subproject in Weblate)
    subprojects = request_get(f"{wsite}projects/{project_name}/components/")
    slugs=[]
    if verbose: print("Getting %d subprojects for %s:"%(subprojects['count'],project_name))
    cnt = len(subprojects['results'])
    while True:
        for sub in subprojects['results']:
            slugs.append(sub['slug'])
        if not subprojects['next']: break
        if verbose: print("  %3d/%3d  %s"%(cnt,subprojects['count'],subprojects['next']))
        subprojects = request_get(subprojects['next'])
        cnt += len(subprojects['results'])

    # get file metadata
    if verbose: print(f"Downloading list of translation files")
    filenamedir={}
    for slug in slugs:
        translations_url = f"{wsite}translations/{project_name}/{slug}/{lang}/"
        retry = 5
        translations = None
        while not translations and retry:
            if verbose: print(f"  Getting metadata for {translations_url}")
            translations = request_get(translations_url)
            retry -= 1
        filename = path.join(project_name, translations['filename'])

        if not filename: 
            ipdb.set_trace()
            continue
        time.sleep(0.5)
        filenamedir[filename] = translations['file_url']

    # save to a json file
    os.makedirs(path.dirname(json_path_name), exist_ok=True)
    with open(json_path_name, "w") as fp:
        json.dump(filenamedir, fp, sort_keys=True, indent=4)

#create path, download file, create hidden file
def download_subproject_files(project_name, lang):
    global wsite, token, redownload_downloaded
    ui_files = load_file_list(project_name, lang)
    
    if verbose: print("Downloading translation files")
    for filename in ui_files:

        if not redownload_downloaded:
            if os.path.exists(filename):
                if verbose: print(f"  Already downloaded, skipping: {filename}")
                continue

        os.makedirs(path.dirname(filename), exist_ok=True)
        url = ui_files[filename]
        #for rep in range(3):
            #response=os.popen(curl_command).read()
        #ipdb.set_trace()
        po_data = ""
        retry=5
        # a po file contains string POT-Creation-Date, so check and retry
        while not "POT-Creation-Date" in po_data and retry:
            if verbose: print(f"  {filename}")
            po_data = request_get(url)
            retry -= 1

        with open(filename, 'w') as f:
            f.write(po_data)
        # create 'backup'of the file for reference - will never be changed
        shutil.copyfile(filename, get_dot_name(filename))

def clear_translations_folder():
    for root, dirs, files in os.walk(f"{os.path.dirname(os.path.abspath(__file__))}/translations", topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

def get_modified_files(flist):
    filecmp.clear_cache()
    modlist=[]
    for fname in flist:
        if not filecmp.cmp(fname, get_dot_name(fname), shallow=False):
            modlist.append(fname)
    return modlist

def transfer_tooltips_ui_to_help():
    #load messages with ahelp strings from help
    ui_files = load_file_list(projects['ui'], lang)
    ahelp_dir ={}
    for ufile in ui_files:
        po = polib.pofile(ufile)
        for entry in po:
            if entry.obsolete: continue
            if "extended" in entry.msgctxt:
                ahelp_id = entry.msgid
                ahelp_str = entry.msgstr
                if ahelp_str:
                    ahelp_dir[ahelp_id] = [ahelp_str, ufile]
                else:
                    ahelp_dir[ahelp_id] = ["", ufile]
                pass
    #load help catalogs and find eventually translated messages in ahelp_dir
    #ipdb.set_trace()
    csvWriter = csv.writer(sys.stdout, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    help_files = load_file_list(projects['help'], lang)
    modified_files = set()
    for hfile in help_files:
        changed = False
        po = polib.pofile(hfile)
        untranslated = po.untranslated_entries()
        for entry in untranslated:
            if entry.obsolete: continue
            if "ahelp" in entry.msgid:
                notags=re.sub(r"<[^<]*>","",entry.msgid)
                ahelp_id=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgid)[0]
                if ahelp_id in ahelp_dir and not entry.msgstr:
                    if ahelp_dir[ahelp_id][0]:   # is translated
                        entry.msgstr = entry.msgid.replace(ahelp_id,ahelp_dir[ahelp_id][0])
                        if notags==ahelp_id:
                            csvWriter.writerow(["Translated", entry.msgid, entry.msgstr])
                        else:
                            csvWriter.writerow(["Partially translated", entry.msgid, entry.msgstr])
                        changed = True
                    else:
                        csvWriter.writerow(["Untranslated", entry.msgid, entry.msgstr])
                    pass
        if changed:
            modified_files.add(hfile)
            po.save(hfile)

def transfer_translations_ui_to_ui():
    #load all messages, organize them by keyid
    ui_files = load_file_list(projects['ui'], lang)
    key_dir ={}
    for ufile in ui_files:
        po = polib.pofile(ufile)
        for entry in po:
            if entry.obsolete: continue
            # keyid is stored in entry.comment
            # store also msgid, to enable checking  
            key_dir[entry.comment] = [entry.msgid, entry.msgstr] 
    #load input catalogs
    csvWriter = csv.writer(sys.stdout, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    input_files = load_file_list(projects[trans_project], lang)
    modified_files = set()
    nmod=0
    for ifile in input_files:
        changed = False
        po = polib.pofile(ifile)
        for entry in po:
            if entry.obsolete: 
                continue
            if entry.comment in key_dir:
                if entry.msgid == key_dir[entry.comment][0]:
                    if entry.msgstr != key_dir[entry.comment][1]:
                        if entry.msgid != key_dir[entry.comment][0]:
                            csvWriter.writerow(["Conflict", entry.msgid, key_dir[entry.comment][0]])
                        csvWriter.writerow(["Replaced", entry.msgid+":", entry.msgstr+" >> "+ key_dir[entry.comment][1]])
                        #ipdb.set_trace()
                        entry.msgstr = key_dir[entry.comment][1]
                        changed=True
                        nmod += 1
                else:
                    csvWriter.writerow(["Conflict", entry.comment, entry.msgid, key_dir[entry.comment][0]])
        if changed:
            modified_files.add(ifile)
            po.save(ifile)

    if modified_files:
        print ("Number of transferred changes: %s"%nmod)
        print ("Modified files:")
        for mf in modified_files:
            print("  %s"%mf)

# key_id is in one of the rows of poentry.comment (usually the first)
def get_key_id_code(poentry):
    key_id = poentry.comment.split("\n")
    if len(key_id) == 1:
        key_id=key_id[0]
    else:
        lenghts = np.nonzero([len(k)==5 for k in key_id])
        key_id=key_id[lenghts[0][0]]
    return key_id

# export unique messages without newlines
# can be used as a glossary in external translation tools as OmegaT
def export_glossary(project):
    global glossary_max
    files = load_file_list(projects[project], lang)
    csvWriter = csv.writer(sys.stdout, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    mset=set()
    for file in files:
        po = polib.pofile(file)
        for entry in po:
            if entry.obsolete: continue

            eid = entry.msgid
            estr = entry.msgstr

            eid = eid.replace("\n",line_break_placeholder)
            if line_break_placeholder in eid: continue 
            estr = estr.replace("\n",line_break_placeholder)
            eid = eid.replace("_","").replace("~","")
            estr = estr.replace("_","").replace("~","")
            # skip long messages
            if glossary_max and len(eid) > glossary_max: continue
            if not eid+estr in mset:
                csvWriter.writerow([eid,estr])
                mset.add(eid+estr)

# compare tag lists, return False on mismatch. Ignore the 'name' attribute (may be translated, which is however not important)
def tag_equivalence(itags, stags):
    if len(itags) != len(stags): return False
    itags=sorted([re.sub(r' name="[^"]*"','',t) for t in itags])
    stags=sorted([re.sub(r' name="[^"]*"','',t) for t in stags])
    if itags != stags:
        #ipdb.set_trace()
        return False
    return True

# build the directory autotranslate_dict from UI data to be used in automatic translation and 
# in tratnslation UI/HELP consistency checking
# autotranslate_dict: "Source string": set of existing translations in UI
def build_autotranslate_dictionary():
    global autotranslate_dict
    files = load_file_list(projects['ui'], lang)
    autotranslate_dict=defaultdict(set)

    # do not include these in translation
    stop_words=["a","this", "and", "or", "to", "from", ".","\\"]
    for file in files:
        po = polib.pofile(file)
        for entry in po:
            if entry.obsolete: continue
            if not entry.translated(): continue
            eid = entry.msgid.replace("~","").replace("_","").replace(":","").lower()
            if eid in stop_words: continue 
            # remove accelerators
            estr = entry.msgstr.replace("~","").replace("_","").replace(":","")
            # add as lower case - owing to usage variants in the help
            autotranslate_dict[eid].add(estr)
    return

# identify and translate string parts according to the UI translations
# return original string with translated UI substrings
def autotrans(msg):
    items = identify_ui_substrings(msg)
    atrans=msg
    for item in items:
        if item.lower() in autotranslate_dict:
            translations = [t for t in autotranslate_dict[item.lower()]]
            #escape regexp control characters
            for c in "[()+*?":
                item=item.replace(c,"[%s]"%c)
            #replace whole words only
            if len(translations) == 1:
                #atrans = re.sub(r"\b%s\b"%item,translations[0],atrans)
                atrans = re.sub(r"%s"%item,translations[0],atrans)
            else:
                #atrans = re.sub(r"\b%s\b"%item,str(translations),atrans)
                atrans = re.sub(r"%s"%item,str(translations),atrans)
            #ipdb.set_trace()
    return atrans

# identify and translate string parts according to the UI translations
# return pairs
def autotrans_list(msg):
    items = identify_ui_substrings(msg)
    atrans=msg
    translations = []
    for item in items:
        if item.lower() in autotranslate_dict:
            translations = [str([item,t]) for t in autotranslate_dict[item.lower()]]
    return translations

# identify substrings existing in the UI component
def identify_ui_substrings(msg):
    #check first if there is an ahelp text.
    # ignore the <ahelp> tag, it is not necessary. 
    msg = re.sub("<AH.>","",msg)
    msg = re.sub("</AH>","",msg)
    msg = re.sub("[0-9]+","",msg)
    # remove special characters - these were tested in help
    #msg = re.sub("[#&=/'+:;%_#*$^!“`°~”@]","",msg)
    #msg = re.sub("[©…]","",msg)
    msg = msg.replace("%PRODUCTNAME","")
    msg = msg.replace("$[officename]","")
    msg = msg.replace("Drag & Drop","Drag and Drop")
    msg = msg.replace("\\","")

    #split to segments at tags and interpunction
    sp="SpLiT"  # split placeholder
    msg_split = re.sub(r"<[^>]*>",sp,msg.replace("–","-"))
    msg_split = re.sub(r"[(){}.,−▸?'|]",sp,msg_split)
    msg_split = msg_split.replace("[",sp)
    msg_split = msg_split.replace("]",sp)
    msg_split = msg_split.replace("-",sp)

    #split in segments
    msg_split = [m.strip() for m in msg_split.split(sp)]
    ui_strings = []
    #for msp in ah_text+msg_split:
    for msp in msg_split:
        if not msp:continue
        # try the whole substring
        if msp.lower() in autotranslate_dict:
            ui_strings += [msp]
        else:
            #split to segments starting with capitalized word
            #ipdb.set_trace()
            segments = segment_string(msp) 
            for segment in segments:
                canditate_seg=[]    #list of candidates from each shortened substring
                # step-by-step shorten by removing the first word
                # to find "Different Paragraph" in the "Different Paragraph Style to an" string
                while len(segment) > 0:
                    rslt = find_ui(segment)
                    if rslt: canditate_seg.append(rslt)
                    #ipdb.set_trace()
                    # remove the first word
                    spacePos = segment.find(" ")
                    if spacePos < 0: 
                        segment = ""
                    else:
                        segment = segment[segment.find(" ")+1:]
                # select the longest candidate substring
                if canditate_seg:
                    lengths = [len(s) for s in canditate_seg]
                    ui_strings.append(canditate_seg[np.argmax(lengths)])
    #select components starting with capital letter
    ui_strings = [ss for ss in ui_strings if ss[0].isupper()]
    return ui_strings

#split string to segments starting with capitalized word
def segment_string(msg):
    if len(msg) < 3: return []
    msg = re.sub(r" +"," ", msg)
    segments=[]
    msgsplit = msg.strip().split(" ")
    segment = ""
    nn = 0
    #ipdb.set_trace()
    while nn < len(msgsplit):
        while nn < len(msgsplit) and msgsplit[nn][0].isupper(): 
            segment = "%s %s"%(segment, msgsplit[nn]) 
            nn += 1
        # 'or' excludes special character, which are neither lower nor upper case
        while nn < len(msgsplit) and (msgsplit[nn][0].islower() or not msgsplit[nn][0].isupper()): 
            segment = "%s %s"%(segment, msgsplit[nn]) 
            nn += 1
        segments.append(segment.strip())
        segment = ""
    return segments

def find_ui(segment):
    #ipdb.set_trace()
    while len(segment) > 0:
        if segment.lower() in autotranslate_dict:
            return segment
        spacePos = segment.rfind(" ")
        if spacePos > 0: 
            segment = segment[:segment.rfind(" ")]
        else:
            return None

#load extra languages for export
def load_extra_languages(llist):
    global trans_project
    trans_dict=defaultdict(list)  # list of dictionaries

    for n in range(len(llist)):
        files = load_file_list(projects[trans_project], llist[n])

        # do not include these in translation
        for file in files:
            po = polib.pofile(file)
            for entry in po:
                if entry.obsolete: continue
                key_id = get_key_id_code(entry)
                # repeated key-ids are possible, add only once
                if len(trans_dict[key_id]) < n+1:
                    trans_dict[key_id].append(entry.msgstr)
    return trans_dict

# write csv row for the variants of the export command
def exportRow(fname, key_id, msgid, msgstr, msgcsrt=""):
    global exportCSVWriter, autotranslate_dict, autotranslate, extra_languages, extra_lang_dictionaries, verify_translation, translator,testcnt
    if extra_languages and not extra_lang_dictionaries:
        extra_lang_dictionaries=load_extra_languages(extra_languages)

    abb_msgid = abbreviate_tags(msgid)[0]
    export_list = [fname,key_id,abb_msgid,abbreviate_tags(msgstr)[0],msgcsrt]
    #if testcnt > 100: sys.exit(1)
    testcnt += 1
    if verify_translation:
        translation = translator.translate([abb_msgid], src="en", dest=lang)[0][1]
        translation = translation.replace("% PR"," %PR")
        sim = similarity(translation, msgstr)
        export_list += [sim,translation]
        #print(sim,translation, msgstr)
        #ipdb.set_trace()
        pass

    if autotranslate:
        if not autotranslate_dict: build_autotranslate_dictionary()
        export_list += autotrans_list(abb_msgid)

    if extra_languages:
        if not extra_lang_dictionaries:
            extra_lang_dictionaries=load_extra_languages(extra_languages)
        export_list = export_list + extra_lang_dictionaries[key_id]

    exportCSVWriter.writerow(export_list)

# export unique messages without newlines
# can be used for offline translation and subsequent import
# can be used as a glossary in external translation tools as OmegaT
def export_inconsistent_tags(project):
    files = load_file_list(projects[project], lang)
    for file in files:
        po = polib.pofile(file)
        for entry in po:
            if entry.obsolete: continue
            if not entry.translated(): continue

            #extract tags
            itags=re.findall(r"<[^/][^>]*>",entry.msgid)
            stags=re.findall(r"<[^/][^>]*>",entry.msgstr)
            if not itags: continue

            if not tag_equivalence(itags, stags):
                key_id = get_key_id_code(entry)
                eid = entry.msgid.replace("\n",line_break_placeholder)
                estr = entry.msgstr.replace("\n",line_break_placeholder)
                #ipdb.set_trace()
                exportRow(file,key_id,eid,estr)
                #test
                abb, adir = abbreviate_tags(eid)
                if adir:
                    eeid = revert_abbreviations(abb,adir)
                    if(eid != eeid):
                        ipdb.set_trace()
                        pass

# export unique messages without newlines
# export messages with inconsisten UI substring translations
def export_inconsistent_ui_trans(project):
    global autotranslate_dict, tooltips_only
    files = load_file_list(projects[project], lang)
    if not autotranslate_dict: build_autotranslate_dictionary()
    for file in files:
        po = polib.pofile(file)
        for entry in po:
            if entry.obsolete: continue
            if not entry.translated(): continue
            if tooltips_only and not ("<ahelp" in entry.msgid or "extended" in entry.msgctxt): continue

            #if entry.msgid == "Menus":
                #ipdb.set_trace()

            failed=False
            ttt=[]
            for item in identify_ui_substrings(entry.msgid):
                #ipdb.set_trace()
                failedItem=True
                if item.lower() in autotranslate_dict:
                    translist = [t for t in autotranslate_dict[item.lower()]]
                    #continue if at least one translation in translist can be found in entry.msgstr
                    for trans in translist:
                        if trans in entry.msgstr: 
                            #ipdb.set_trace()
                            failedItem=False
                            break
                        else:
                            ttt.append(trans)
                    if failedItem: 
                        #if we are here, no translation in translist was found in msgstr
                        key_id = get_key_id_code(entry)
                        eid = entry.msgid.replace("\n",line_break_placeholder)
                        estr = entry.msgstr.replace("\n",line_break_placeholder)
                        exportRow(file,key_id,eid,estr,str(ttt))
                        break

            #ipdb.set_trace()
            pass


#abbreviate tags
#Replace
#<ahelp hid=".">The <emph>Format</emph> menu contains commands for formatting selected cells, <link href="text/shared/00/00000005.xhp#objekt" name="objects">objects</link>, and cell contents in your document.</ahelp>'
#by
#'<AH0>The <EM0>Format</EM> menu contains commands for formatting selected cells, <LI0>objects</LI>, and cell contents in your document.</AH>'
def abbreviate_tags(imsg):
    if no_abbreviation: return imsg, None
    # directory of replacements, to be used in removal of abbreviations
    adir ={}
    msg=imsg
    for tag in abb_tags:
        ftags=re.findall(r"<%s[^>]*>"%tag,msg)
        for n in range(len(ftags)):
            abb="%s%d"%(tag[:2].upper(),n)
            msg = msg.replace(ftags[n],"<%s>"%abb,1)
            adir["<%s>"%abb]=ftags[n]
        msg = msg.replace("</%s>"%tag, "</%s>"%tag[:2].upper())
    #ipdb.set_trace()
    return msg, adir

#revert abbreviations in msgstr
# adir: abbreviation generated from the corresponding msgid 
def revert_abbreviations(abb_str, adir):
    msgstr = abb_str
    nrev=0  #number of reverted tags
    for a in adir:
        aux = msgstr.replace(a,adir[a])
        if aux != msgstr: nrev += 1
        msgstr = aux
    if nrev != len(adir):
        print(f'  Import error: abbreviation reverting failed, not all abbreviations were found.')
        print(f'\tThe msgid and msgstr parts probably do not match')
        print('\tInput: %s'%abb_str)
        print('\tFailed: %s'%msgstr)
        print('\tDelete this row from the csv file, reset changes and import again')
        sys.exit(1)
    for tag in abb_tags:
        msgstr = msgstr.replace("</%s>"%tag[:2].upper(),"</%s>"%tag) 
    #ipdb.set_trace()
    # check if abbreviations still exist
    for tag in abb_tags:
        if "<%s"%tag[:2].upper() in msgstr:
            print(f'  Import error: abbreviation reverting failed, not all abbreviations were removed.')
            print(f'\tThe msgid and msgstr parts probably do not match')
            print('\tInput: %s'%abb_str)
            print('\tFailed: %s'%msgstr)
            print('\tDelete this row from the csv file, reset changes and import again')
            sys.exit(1)

    return msgstr

# export unique messages without newlines
# can be used for offline translation and subsequent import
# can be used as a glossary in external translation tools as OmegaT
def export_messages_to_csv(project):
    files = load_file_list(projects[project], lang)
    for file in files:
        try:
            po = polib.pofile(file)
        except OSError as err:
            print("OS error: {0}".format(err), file=sys.stderr)
            continue
        for entry in po:
            if entry.obsolete: continue
            if untranslated_only and entry.msgstr: continue

            if tooltips_only and not ("<ahelp" in entry.msgid or "extended" in entry.msgctxt): continue
            eid = entry.msgid
            estr = entry.msgstr
            key_id = get_key_id_code(entry)

            eid = eid.replace("\n",line_break_placeholder)
            estr = estr.replace("\n",line_break_placeholder)
            msgctxt = entry.msgctxt.replace("\n",line_break_placeholder)
            exportRow(file,key_id,eid,estr,msgctxt)

# export conflicting translations
def export_conflicting_messages_to_csv(project):
    files = load_file_list(projects[project], lang)
    # dictionary with potentially conflicting entries (if len>1)
    conf_dict = defaultdict(list)
    # a set to detect repetitions
    repetitions = set()
    for fname in files:
        po = polib.pofile(fname)
        for entry in po:
            key_id = get_key_id_code(entry)

            if entry.obsolete: continue
            if tooltips_only and not ("<ahelp" in entry.msgid or "extended" in entry.msgctxt): continue

            if trans_project == 'ui':
                #remove newlines
                eid = entry.msgid.replace("\n",line_break_placeholder)
                estr = entry.msgstr.replace("\n",line_break_placeholder)
            else: #help
                if tooltips_only:
                    eid=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgid)
                    estr=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgstr)
                    if not estr: continue
                    eid=eid[0]
                    estr=estr[0]
                else:
                    eid=entry.msgid
                    estr=entry.msgstr
                #ipdb.set_trace()

            # ignore untranslated
            if not estr: continue
            
            if conflicts_only_rev:
                aux=eid
                eid=estr
                estr=aux
                pass
            #add to the dictionary
            #if eid+estr.lower() not in repetitions: #ignore case in estr when detecting conflicts
                #repetitions.add(eid+estr.lower())
                #conf_dict[eid].append([fname, key_id, estr])
            conf_dict[eid].append([fname, key_id, estr, entry.msgctxt])
    # export only those with more than one entry
    for eid in conf_dict:
        # export only conflicting translations
        if conflicts_only_rev:
            unique = set()
            for val in conf_dict[eid]: unique.add(val[2].lower().replace("_","").replace("~","").replace("-"," "))
            if len(unique) > 1:
                for val in conf_dict[eid]:
                    exportRow(val[0], val[1], val[2], eid, val[3])
        else:
            unique = set()
            for val in conf_dict[eid]: unique.add(val[2])
            if len(unique) > 1:
                #ipdb.set_trace()
                for val in conf_dict[eid]:
                    exportRow(val[0], val[1], eid, val[2], val[3])

#export translated tooltips, if they are translated on the 'other' side
#useful if tooltips on the 'other' side (help) were of poor quality, but still transferred to ui
def export_etips_trans_help():
    #load messages with ahelp strings from help
    help_files = load_file_list(projects['help'], lang)
    ahelp_dir ={}
    for hfile in help_files:
        po = polib.pofile(hfile)
        for entry in po:
            if entry.obsolete: continue
            if "ahelp" in entry.msgid:
                ahelp_id=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgid)[0]
                ahelp_str=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgstr)
                if ahelp_str:
                    ahelp_dir[ahelp_id] = [ahelp_str[0], hfile]
                pass
    #load ui catalogs and find if they have translated counterpart in help
    ui_files = load_file_list(projects['ui'], lang)
    for uifile in ui_files:
        po = polib.pofile(uifile)
        for entry in po:
            if not "extended" in entry.msgctxt: continue
            if entry.msgid in ahelp_dir and entry.msgstr:
                csvWriter.writerow([uifile, entry.comment, entry.msgid, entry.msgstr])

def strip_interpuct_end(txt, inp):
    while txt[-1] in inp and len(txt) > 1:
        txt = txt[:-1]
    return txt

# unifies message trailing chracters and removes extra space in a message
# the fixes were adjusted to the actual situation in the  Slovak translation
# prior to upload check the result using etiptrans.py -p ui diff
def fix_trailing_characters(project):
    files = load_file_list(projects[project], lang)
    modified_files = set()
    for file in files:
        changed = False
        po = polib.pofile(file)
        for entry in po:
            if not entry.msgstr or entry.obsolete:
                continue
            #remove trailing interpunction
            if entry.msgid in ["...", "'", ".", ":", "!"]:
                continue
            # add interpunction from msgid
            if entry.msgid[-3:] == "...":
                msgstr = strip_interpuct_end(entry.msgstr,".…:")
                entry.msgstr = msgstr+"..."
                changed = True
            elif entry.msgid[-1] == "…":
                msgstr = strip_interpuct_end(entry.msgstr,".…")
                entry.msgstr = msgstr+"..."
                changed = True
            elif entry.msgid[-1] in ".":
                msgstr = strip_interpuct_end(entry.msgstr,",. !")
                entry.msgstr = msgstr+entry.msgid[-1]
                changed = True
            elif entry.msgid[-1] in ":":
                msgstr = strip_interpuct_end(entry.msgstr," :")
                entry.msgstr = msgstr+entry.msgid[-1]
                changed = True
            elif entry.msgid[-1] in "!":
                msgstr = strip_interpuct_end(entry.msgstr," !.")
                entry.msgstr = msgstr+entry.msgid[-1]
                changed = True
            elif entry.msgid[-1] in " ":
                msgstr = strip_interpuct_end(entry.msgstr," ")
                entry.msgstr = msgstr+entry.msgid[-1]
                changed = True
            else:
                if entry.msgstr[-1] in ".: ":
                    if entry.msgstr[-3:] == '...':
                        entry.msgstr = entry.msgstr[:-3]
                    else:
                        entry.msgstr = entry.msgstr[:-1]
                    changed = True
                    pass
            # fix spaces
            if "  " in entry.msgstr:
                entry.msgstr = entry.msgstr.replace("  ", " ")
                changed = True
            if " , " in entry.msgstr:
                entry.msgstr = entry.msgstr.replace(" , ", ", ")
                changed = True
            if entry.msgstr[0] == " " and entry.msgid[0] != " ":
                entry.msgstr = entry.msgstr[1:]
                changed = True
        if changed:
            modified_files.add(file)
            po.save(file)
    if modified_files:
        print ("Modified files:")
        for mf in modified_files:
            print("  %s"%mf)

#check correctness
#if tags and interpunction is removed, number of words must be the same
def check_removed_spaces(intext, text):
    icnt = re.sub(r"<[^>]*>","", intext)
    icnt = re.sub(r"[,.$%()]","", icnt)
    icnt = re.sub(r"  *"," ", icnt)
    ocnt = re.sub(r"<[^>]*>","", text)
    ocnt = re.sub(r"[,.$%()]","", ocnt)
    ocnt = re.sub(r"  *"," ", ocnt)
    if icnt == ocnt: return #e.g. both are empty
    if icnt[0] == " ": icnt=icnt[1:]
    if icnt[-1] == " ": icnt=icnt[:-1]
    if ocnt[0] == " ": ocnt=ocnt[1:]
    if ocnt[-1] == " ": ocnt=ocnt[:-1]
    icnts = icnt.split(" ")
    ocnts = ocnt.split(" ")
    if len(icnts) != len(ocnts):
        print(icnts)
        print(ocnts)
        print(f'\n%s import error: correction of modifications potentially caused by a translating service failed')
        print('\tOriginal: %s'%intext)
        print('\tCorrected: %s'%text)
        print('\tDelete this row from the csv file, reset changes and import again')
        sys.exit(1)

# If the Google translation service was used to translate strings, it is necessary to fix certain errors 
def remove_extra_spaces(intext):
    #$ [officename]
    text = intext.replace("$ [office","$[office")
    text = text.replace("% PRODUCTNAME"," %PRODUCTNAME")
    #< / switchinline>
    text = text.replace("< / ","</")
    #function
    text = text.replace(" ()","()")
    #leading space
    text = re.sub(r"^ *","",text)
    #trailing space
    text = re.sub(r" *$","",text)
    #spaces after opening tag
    tag_first="evalsbicd"   #first letters of tags present in help
    text = re.sub(r"(<[%s][^>]*>) "%tag_first, r"\1",text)
    #spaces before closing tag
    text = re.sub(r" (</[%s][^>]*>)"%tag_first, r"\1",text)
    # fix stuff inside tags
    tags=re.findall(r"<[%s][^>]*>"%tag_first,text)
    for tag in tags:
        text=text.replace(tag,tag.replace(" = ","=").replace(" / ","/"))

    check_removed_spaces(intext, text)
    return text

def import_translations(project):
    with open(csv_import, 'rt', encoding='utf-8') as ifile:
        reader = csv.reader(ifile, delimiter='\t', quotechar='"',quoting=csv.QUOTE_MINIMAL)
        import_dir = None
        ncols=0
        #Expected header
        hdr=["File name","KeyID","Source","Target"]
        for row in reader:
            if import_dir is None: 
                if row[:4] != hdr:
                    print(f'\n%s import error: incorrect table header, expected "%s,%s,%s,%s".'%tuple([sys.argv[0]]+hdr))
                    sys.exit(1)
                else:
                    import_dir = {}
                    continue
            if len(row) < 4:
                ipdb.set_trace()
                print(f"\n%s import error: insufficient number of columns at %s."%(sys.argv[0], row))
                sys.exit(1)
            import_dir[row[1]] = row[2:]

    #load ui catalogs and replace msgstr of those with identical keyid
    pofiles = load_file_list(projects[project], lang)
    modified_files = set()
    ntrans=0
    for pofile in pofiles:
        changed = False
        po = polib.pofile(pofile)   #load messages from the file
        for entry in po:
            if entry.obsolete: continue
            keyid = get_key_id_code(entry)
            if not keyid in import_dir: continue
            #remove abbreviations in translated strings. If there are none, nothing happens
            aux, adir = abbreviate_tags(entry.msgid)
            #ipdb.set_trace()
            msgstr = revert_abbreviations(import_dir[keyid][1],adir)
            entry.msgstr = remove_extra_spaces(msgstr).replace(line_break_placeholder,"\n")
            changed = True
            ntrans += 1
            if entry.msgstr:
                print("  Replaced translation: %s"%(entry.msgid))
            else:
                print("  New translation: %s"%(entry.msgid))
        if changed:
            modified_files.add(pofile)
            po.save(pofile)

    if modified_files:
        print ("Number of imported translations: %s"%ntrans)
        print ("Modified files:")
        for mf in modified_files:
            print("  %s"%mf)

def transfer_tooltips_help_to_ui():
    #load messages with ahelp strings from help
    help_files = load_file_list(projects['help'], lang)
    ahelp_dir ={}
    for hfile in help_files:
        po = polib.pofile(hfile)
        for entry in po:
            if entry.obsolete: continue
            if "ahelp" in entry.msgid:
                ahelp_id=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgid)[0]
                ahelp_str=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgstr)
                if ahelp_str:
                    ahelp_dir[ahelp_id] = [ahelp_str[0], hfile]
                else:
                    ahelp_dir[ahelp_id] = ["", hfile]
                pass
    #load ui catalogs and find eventually translated messages in ahelp_dir
    ui_files = load_file_list(projects['ui'], lang)
    modified_files = set()
    for uifile in ui_files:
        changed = False
        po = polib.pofile(uifile)
        untranslated = po.untranslated_entries()
        for entry in untranslated:
            if entry.msgid in ahelp_dir and not entry.msgstr:
                #ipdb.set_trace()
                if ahelp_dir[entry.msgid][0]:
                    #ipdb.set_trace()
                    entry.msgstr = import_dir[entry.msgid][0].replace(line_break_placeholder,"\n")
                    print("  Translated: %s"%(entry.msgid))
                    changed = True
                else:
                    print("Untranslated in  '%s': '%s'"%(ahelp_dir[entry.msgid][1], entry.msgid))
                pass
        if changed:
            modified_files.add(uifile)
            po.save(uifile)

    if modified_files:
        print ("Modified files:")
        for mf in modified_files:
            print("  %s"%mf)

def load_file_list(trans_project, lang):
    with open(path.join(trans_project, lang, 'files.json'), "r") as fp:
        proj_files = json.load(fp)
    return proj_files

# class to be used in translations using the google.cloud service
class Trans():
    def __init__(self, type="google.cloud", source_lang = "en-US"):
        self.type = type
        self.source_lang = source_lang
        if self.type == "google.cloud":
            #sudo pip3 install google-cloud-translate
            from google.cloud import translate
            from difflib import SequenceMatcher
            project_id="libreoffice-sk-en-465"
            self.client = translate.TranslationServiceClient()
            self.parent = self.client.location_path(project_id, "global")
        elif self.type == "googletrans":
            from googletrans import Translator
            self.translator = Translator(service_urls=[ 'translate.google.com', ])
 
    def translate(self, messages, src, dest): 
        if self.type == "google.cloud":
            try:
                response = self.client.translate_text(
                    parent=self.parent,
                    contents=messages,
                    mime_type="text/html",  # mime types: text/plain, text/html
                    #mime_type="text/html",
                    source_language_code=src,
                    target_language_code=dest
                )
            except Exception as e:
                print("Translation service failed")
                # continue - from the number of repetiotions one can estimate the amount of not translated strings 
                return None
            return [(m,r.translated_text) for m,r in zip(messages,response.translations)]
        elif self.type == "googletrans":
            try:
                response = self.translator.translate(messages, dest=dest)
            except Exception as e:
                print("Translation service failed")
                # continue - from the number of repetiotions one can estimate the amount of not translated strings 
                return None
            return [(r.origin,r.text) for r in response]

def similarity(a, b): return SequenceMatcher(None, a, b).ratio()

projects = {
        'help': "libo_help-master",
        'ui': "libo_ui-master",
        'ui70': "libo_ui-7-0",
        'ui64': "libo_ui-6-4",
        'ui63': "libo_ui-6-3"
        }
trans_project=None

#list of used tags used in help
abb_tags = [
        "ahelp",
        "bookmark_value",
        "caseinline",
        "embedvar",
        "font",
        "item",
        "link",
        "switchinline",
        "variable",
        "defaultinline", 
        #"emph", 
        "literal", 
        "image", 
        "alt", 
        "menuitem"
        ]
    

pname = "libo_help-master"
# necessary only if the -y switch is used (verify translation...)
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
api_key = os.environ.get('WEBLATE_API_KEY')
lang = os.environ.get('WEBLATE_API_LANG')
wsite = os.environ.get('WEBLATE_API_SITE')
#wsite = f"https://translations.documentfoundation.org/api/"
verbose = True  #set to True, otherwise needs a deeper analysis
csv_import=""
conflicts_only=False
conflicts_only_rev=False
tooltips_only=False
translated_other_side=False
inconsistent_tags=False
no_abbreviation=False
autotranslate=False
inconsistent_ui_trans=False
autotranslate_dict=None #dictionary to hold all UI translations
transfer_from=""
exportCSVWriter=None
extra_languages=[]
extra_lang_dictionaries=[]
verify_translation=False
translator = None
testcnt=0   #limit in testing
untranslated_only = False
redownload_downloaded = False
glossary_max=0

#placeholder to mark line breaks in export
line_break_placeholder="<LINE_BREAK>"

def main():
    global token, exportCSVWriter, no_abbreviation, translator

    #response = http.get("https://en.wikipedia.org/w/api.php")
    action = parsecmd()
    if action: action=action[0][:2]

    if action != "he" and not trans_project in projects:
        print(f"\n%s error: translation project not specified."%sys.argv[0])
        usage()
        sys.exit(1)

    if not api_key:
        print("\n%s error: no API key"%sys.argv[0])
        print("  Set environment variable WEBLATE_API_KEY or use the -k switch.") 
        usage()
        sys.exit(1)
    token = 'Token '+api_key

    if not wsite:
        print("\n%s error: no API key"%sys.argv[0])
        print("  Set environment variable WEBLATE_API_SITE or use the -s switch.") 
        usage()
        sys.exit(1)

    if not lang:
        print("\n%s error: no API key"%sys.argv[0])
        print("  Set environment variable WEBLATE_API_LANG or use the -l switch.") 
        usage()
        sys.exit(1)

    if action == "do":  #download
        download_subproject_file_list(projects[trans_project], lang)
        download_subproject_files(projects[trans_project], lang)
        pass

    elif action == "mo":    #modified
        proj_files = load_file_list(projects[trans_project], lang)
        modified_files = get_modified_files(proj_files.keys())
        print("Modified files in %s:"%projects[trans_project])
        for mfile in modified_files:
            print("\t%s"%mfile)
        pass

    elif action == "di":    #differences
        proj_files = load_file_list(projects[trans_project], lang)
        modified_files = get_modified_files(proj_files.keys())
        for mfile in modified_files:
            print("Differences in  %s:"%mfile)
            #load original messagaes
            po = polib.pofile(get_dot_name(mfile))
            orig_dir ={}
            num = 0
            for entry in po:
                orig_dir["%04d %s"%(num,entry.msgid)] = entry.msgstr
                num += 1

            #compare modified messagaes
            po = polib.pofile(mfile)
            num = 0
            for entry in po:
                if orig_dir["%04d %s"%(num,entry.msgid)] != entry.msgstr:
                    print("\t'%s'"%entry.msgid)
                    print("\t< '%s'"%orig_dir["%04d %s"%(num,entry.msgid)])
                    print("\t> '%s'"%entry.msgstr)
                    print()
                num += 1

    elif action == "re":    #revert
        proj_files = load_file_list(projects[trans_project], lang)
        modified_files = get_modified_files(proj_files.keys())
        if modified_files:
            print("Reverting files:")
            for fname in modified_files:
                print("\t%s"%fname)
                shutil.copyfile(get_dot_name(fname), fname)
        else:
            print("No files to revert.")

    elif action == "tr":    #transfer translations
        if trans_project == "ui" and transfer_from == "help":
            transfer_tooltips_help_to_ui()
        elif trans_project == "help" and transfer_from == "ui":
            transfer_tooltips_ui_to_help()
        elif trans_project[:2] == "ui" and transfer_from == "ui":
            transfer_translations_ui_to_ui()
        else:
            print("\n%s error: You can transfer translations only from 'help' to 'ui', from 'ui' to 'help' and from 'ui' to other 'ui' projects."%sys.argv[0])
            print("\n%s error: You wanted to transfer translations from '%s' to '%s'."%(sys.argv[0], transfer_from, trans_project))
            usage()

    elif action == "im":    #import translations from csv file (-c switch)
        if not csv_import:
            print("\n%s import error: specify a csv file with translation'."%sys.argv[0])
            usage()
        else:
            if trans_project == "ui":
                import_translations("ui")
            else:
                import_translations("help")

    elif action == "up":    #upload
        proj_files = load_file_list(projects[trans_project], lang)
        modified_files = get_modified_files(proj_files.keys())
        for fpath in modified_files:
            upload_file(fpath, proj_files[fpath])
            #rewrite the old dot file
            shutil.copyfile(fpath, get_dot_name(fpath))
        pass

    elif action == "gl":    #glossary
        export_glossary(trans_project)

    elif action == "ex":    #export
        if verify_translation:
            translator = Trans("google.cloud")
        if trans_project == 'ui': no_abbreviation = True
        exportCSVWriter = csv.writer(sys.stdout, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        exportCSVWriter.writerow(['File name', 'KeyID', 'Source', 'Target'])
        if conflicts_only or conflicts_only_rev:
            export_conflicting_messages_to_csv(trans_project)
        elif inconsistent_tags:
            export_inconsistent_tags(trans_project)
        elif inconsistent_ui_trans:
            export_inconsistent_ui_trans(trans_project)
        elif translated_other_side:
            if trans_project == "ui":
                export_etips_trans_help()
            else:
                print("\n%s: not implemented yet for help'."%sys.argv[0])
        else:
            export_messages_to_csv(trans_project)

    elif action == "fi":    #fix trailing characters
        fix_trailing_characters(trans_project)

    elif action == "he":    #help
        print("he")
        usage()
        pass

    else:
        if not autotranslate_dict: build_autotranslate_dictionary()
        teststrings=[
                "oLabel1.Text =",
                "Drag & Drop",
                "%PRODUCTNAME and Microsoft Office",
                "<AH0>Updates the links in the current document.</AH>",
                "To Apply a Different Paragraph Style to an Index Level",
                "Choose <IT0>View - Toolbars- Drawing</IT> to open the <IT1>Drawing</IT> toolbar.",
                "<AH0>Starts the Mail Merge Wizard to create form letters or Send Email Messages to Many Recipients require.</AH>",
                "xxx Direct Cursor Mode",
                "To replace Colors with the Color Replacer tool",
                "<AH0>Adds the selected field from the Address Elements list to the other list.</AH> You can add the same field more than once.",
                "<AH0>Opens the <LI0>New Address List</LI> dialog, where you can edit the selected address list.</AH>",
                "<AH0>Opens the <emph>Mail Merge Recipients</emph> dialog.</AH>",
                "Choose <emph>Format - Frame and Object - Properties - Options</emph>.",
                "To Switch off the Word Completion",
                "<LI0>Footnote and Endnote</LI>",
                "Frame",
                "<VA0><AH0>Wraps text around the shape of the object. This option is not available for the <emph>Through</emph> wrap type, or for frames.</AH> To change the contour of an object, select the object, and then choose <emph>Format - Wrap - </emph><LI0><emph>Edit Contour</emph></LI>.</VA>",
                "Toggle Direct Cursor Mode",
                ]
        for test in teststrings:
            items = identify_ui_substrings(test)
            print(test,items)

        #print("\n%s error: unspecified action '%s'."%(sys.argv[0],action))
        #usage()


if __name__ == "__main__":
    main()
