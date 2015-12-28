#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import zipfile
import random

from lxml import etree
from lxml import html
from pprint import pprint
from yattag import indent
from yattag import Doc
from lxml.html.clean import Cleaner

#import fromMD

def write_iframe_code(video_link):
    return '<p><iframe allowfullscreen="" mozallowfullscreen="" webkitallowfullscreen="" data-src="'+video_link+'"></iframe></p>'
    

def parse_content(href, module=False, rewrite_iframe_src=True):
    """ open file and replace media links and src for iframes """
    if not module:
        module = ""

    with open(href, 'r') as file:
        htmltext = file.read()

    tree = html.fromstring(htmltext)
    # Rewrite image links: for each module file, media dir is one step above (../media/)
    # with html export, medias are accessed from index.html in root dir, so we have 
    # to reconstruct the whole path
    try:
        for element, attribute, link, pos in tree.iterlinks():
            newlink = link.replace("../media", module+"/media")
            element.set(attribute, newlink)
    except Exception as e:
        print("Exception rewriting/removing links %s" % (e))

    # FIXME: this should be removed, since obsolete : removing "Retour au cours" links
    try:
        links = tree.xpath('//a[contains(@href, "COURSEVIEWBYID")]')
        for l in links:
            l.getparent().remove(l)
    except:
        print("Exception with moodle courses links")
        pass

    # rename iframe attribute to prevent loading all iframes at once
    # FIXME : should be removed since iframes are generated in another place now
    if rewrite_iframe_src:
        try:
            iframes = tree.xpath('//iframe')
            for iframe in iframes:
                iframe.attrib['data-src'] = iframe.attrib['src']
                etree.strip_attributes(iframe, 'src')
        except Exception as e:
            print("Exception with iframe src")
            pass

    return html.tostring(tree, encoding='utf-8').decode('utf-8')

def generateMenuSubsections(subsections,doc,tag,text):
    # looping through subsections, skipping non html files
    for subsection in subsections:
        # 1st subsection active by default
        if subsection['num'].endswith('-1'):
            active_sub = " active"
        else:
            active_sub = ""
        try:
            href = subsection['filename']
        except:
            href = ""
        try:
            videos = subsection['videos']
        except:
            videos = []
        if href.endswith(".html") or len(videos) > 0:
            subsection_id = "subsec_"+subsection['num']
            if subsection['folder'] != 'correction':
                with tag('a', href="#", data_sec_id=subsection_id, klass="subsection "+subsection['folder']+active_sub):
                    text(subsection['title'])


def generateMenuSections(data,doc,tag,text): 
    for section in data["sections"]:
        # 1st section active by default
        if section['num'] == "1":
            active_sec = " active"
            display = " display:block"
        else:
            active_sec = ""
            display = ""
        try:
            source_file = section['filename']
            if len(source_file) > 0:
                section_id = "sec_"+section['num']
            else:
                section_id = ""
        except:
            section_id = ""
        with tag('li'):
            with tag('a', href="#", data_sec_id=section_id, klass="section"+active_sec):
                text(section['title'])
            with tag('p', style=display):
                generateMenuSubsections(section['subsections'],doc,tag,text)

def generateVideo(doc,tag,text,videos,display,subsection,subsec_text):
    for idVid, video in enumerate(videos):
        # go now line for each video after 1st video
        if idVid > 0:
            doc.asis('<br />')
        # add iframe code
        iframe_code = write_iframe_code(video['video_link'])
        if display: # for very first subsection, keep normal iframe src 
            iframe_code = iframe_code.replace('data-src', 'src')
        doc.asis(iframe_code)
        doc.asis("\n\n")
        # add text only 1st time
        if idVid == 0:
            # add text in fancybox lightbox

            text_id = subsection['num']+"_"+str(idVid)
            with tag('div', klass="inline fancybox", href="#"+text_id):
                text('Version Texte du cours')
                with tag('div', klass="mini-text"):
                    doc.asis(subsec_text)
            with tag('div', style="display:none"):
                with tag('div', id=text_id, klass="fancy-text"):
                    doc.asis(subsec_text)

def generateSubsectionContent(section,subsection,doc,tag,text):
        # load 1st subsec by default, rest is hidden
        if subsection['num'].endswith('.1'):
            display = "true"
        else:
            display = "none"
        subsection_id = "subsec_"+subsection['num']
        with tag('section', id=subsection_id, style="display:"+display):
            # fil d'arianne
            with tag('p', klass='fil_ariane'):
                text(section['title']+' | '+subsection['title'])
            try:
                href = module_folder+'/'+subsection['filename']
                subsec_text = parse_content(href, module_folder)
            except:
                href = ""
                subsec_text = ""
            # If there are videos, rendering differs, as we put subsection text in a fancybox reader along with video iframes  
            if "videos" in subsection :
                generateVideo(doc,tag,text,subsection["videos"],display,subsection,subsec_text)
            else: # print subsection text asis                        
                if href.endswith(".html"):
                    doc.asis(subsec_text)
    
                    
def generateMainContent(data, doc,tag,text):
    # Print main content
    doc.asis('<!--  MAIN CONTENT -->')
    with tag('main', klass="content"):
        # Loop through sections
        for section in data["sections"]:
            
            section_id = "sec_"+section['num']
            try:
                href = module_folder+'/'+section['filename']
                with tag('section', id=section_id, style=("display:none")):
                    doc.asis(parse_content(href, module_folder))
            except:
                print (" ---- no content for section %s" % (section_id))
            # Loop through subsections
            for subsection in section['subsections']:
                if subsection['folder'] != 'correction':
                    generateSubsectionContent(section,subsection,doc,tag,text)


def writeHtml(module_folder,doc):
    module_file_name = module_folder+'/'+module_folder+'.html'
    moduleHtml = open(module_file_name, 'w')
    moduleHtml.write(indent(doc.getvalue()))
    moduleHtml.close()
    
def generateModuleHtml(data, module_folder=False):
    """ parse data from config file 'moduleX.config.json' and generate a moduleX html file """

    # create magic yattag triple
    doc, tag, text = Doc().tagtext()

    doc.asis('<!--  NAVIGATION MENU -->')
    with tag('nav', klass="menu accordion"):
        with tag('h3'):
            text(data["lom_metadata"]["title"])
        with tag('ul'):
            generateMenuSections(data,doc,tag,text)
            
    generateMainContent(data,doc,tag,text)
    writeHtml(module_folder,doc)
    
def usage():
    str = """
        Usage:
           toHTML.py config_filein [OPTIONS]
           - if ommited, default config file is "toHTMLgobal.config.json"
           - exporte les fichiers depuis l'arborescence git + fichier de config pour en
           faire un fichier HTML module.html pour chaque [module] défini en config
           
           OPTIONS: 
           -md : parses markdown file found in module_folder given in argument 
           
    """
    print (str)
    exit(1)

def main(args):
    """
        toHTML is a utility to help building HTML export of course material
        given a config file with sections structure + some other parameters
        FIXME : add option -m with module folder to generate all HTML sources + module html file
    """
    
    # filein is a global config file that gives each module's parameters
    if len(args) == 1:
        filein = args[0]
    elif len(args) < 1:
        filein = 'toHTMLglobal.config.json'
    else:
        usage()
    
    with open(filein, encoding='utf-8') as global_config:
        # load module data from filin
        global_data = json.load(global_config)
    for module in global_data["modules"]:
        # generate config file with fromMD script/library
        #if '-md' in sys.argv:
        #### TODOO scripts.fromMD.main([module["folder"]])
        # config file for eaxh module is nammed [module_folder].config.json
        mod_config = os.path.join(module["folder"], module["folder"]+'.config.json')
        with open(mod_config, encoding='utf-8') as mod_data_file:
            # load module data from filin
            mod_data = json.load(mod_data_file)

        # print(" Data loaded \n %s" % (data) )
        generateModuleHtml(mod_data, module["folder"])
    print (" index.html saved. Compressing archive in %s " % (os.getcwd()))

############### main ################
if __name__ == "__main__":
    main(sys.argv[1:])
