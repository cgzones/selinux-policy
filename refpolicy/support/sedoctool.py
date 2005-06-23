#!/usr/bin/python

#  Author: Joshua Brindle <jbrindle@tresys.com>
#
# Copyright (C) 2003 - 2005 Tresys Technology, LLC
#      This program is free software; you can redistribute it and/or modify
#      it under the terms of the GNU General Public License as published by
#      the Free Software Foundation, version 2.

"""
	This module generates configuration files and documentation from the 
	SELinux reference policy XML format. 
"""

import sys
import getopt
import pyplate
import os
import string
from xml.dom.minidom import parse, parseString

def read_policy_xml(filename):
	try:
		xml_fh = open(filename)
	except:
		error("error opening " + filename)

	try:
		doc = parseString(xml_fh.read())
	except: 
		xml_fh.close()
		error("Error while parsing xml")

	xml_fh.close()	
	return doc

def gen_tunable_conf(doc, file):
	for node in doc.getElementsByTagName("tunable"):
		s = string.split(format_txt_desc(node), "\n")
		for line in s:
			file.write("# %s\n" % line)
		tun_name = tun_val = None
        	for (name, value) in node.attributes.items():
			if name == "name":
				tun_name = value
			elif name == "dftval":
				tun_val = value

			if tun_name and tun_val:
	            		file.write("%s = %s\n\n" % (tun_name, tun_val))
				tun_name = tun_val = None

def gen_module_conf(doc, file):
	file.write("#\n# This file contains a listing of available modules.\n")
	file.write("# To prevent a module from  being used in policy\n")
	file.write("# creation, uncomment the line with its name.\n#\n")
	for node in doc.getElementsByTagName("module"):
		mod_name = mod_layer = None

		mod_name = node.attributes.items()[0][1]
		mod_layer = node.parentNode.attributes.items()[0][1]

		if mod_name and mod_layer:
			file.write("# Layer: %s\n# Module: %s\n#\n" % (mod_layer,mod_name))
		for desc in node.getElementsByTagName("summary"):
			if not desc.parentNode == node:
				continue
			s = string.split(format_txt_desc(desc), "\n")
			for line in s:
				file.write("# %s\n" % line)	
			file.write("#%s\n\n" % mod_name)

def stupid_cmp(a, b):
	return cmp(a[0], b[0])

def int_cmp(a, b):
	return cmp(a["interface_name"], b["interface_name"])
			
def gen_doc_menu(mod_layer, module_list):
	menu = []
	for layer, value in module_list.iteritems():
		cur_menu = (layer, [])
		menu.append(cur_menu)
		if layer != mod_layer and mod_layer != None:
			continue
		#we are in our layer so fill in the other modules or we want them all
		for mod, desc in value.iteritems():
			cur_menu[1].append((mod, desc))

	menu.sort(stupid_cmp)
	for x in menu:
		x[1].sort(stupid_cmp)
	return menu

def format_html_desc(node):

	desc_buf = ''
	for desc in node.childNodes:
		if desc.nodeName == "#text":
			if desc.data is not '':
				desc_buf += "<p>" + desc.data + "</p>"
		elif desc.nodeName == "p":
			if desc.firstChild.data is not '':
				desc_buf += "<p>" + desc.firstChild.data + "</p>"
			for chld in desc.childNodes: 
				if chld.nodeName == "ul":
					desc_buf += "<ul>"
					for li in chld.getElementsByTagName("li"):
						desc_buf += "<li>" + li.firstChild.data + "</li>"
					desc_buf += "</ul>"

	return desc_buf

def format_txt_desc(node):

	desc_buf = ''
	for desc in node.childNodes:
		if desc.nodeName == "#text":
			desc_buf += desc.data + "\n"
		elif desc.nodeName == "p":
			desc_buf += desc.firstChild.data + "\n"
			for chld in desc.childNodes: 
				if chld.nodeName == "ul":
					desc_buf += "\n"
					for li in chld.getElementsByTagName("li"):
						desc_buf += "\t -" + li.firstChild.data + "\n"

	return desc_buf

def gen_docs(doc, dir, templatedir):

	try:
		#get the template data ahead of time so we don't reopen them over and over
		bodyfile = open(templatedir + "/header.html", "r")
		bodydata = bodyfile.read()
		bodyfile.close()
		intfile = open(templatedir + "/interface.html", "r")
		intdata = intfile.read()
		intfile.close()
		menufile = open(templatedir + "/menu.html", "r")
		menudata = menufile.read()
		menufile.close()
		indexfile = open(templatedir + "/module_list.html","r")
		indexdata = indexfile.read()
		indexfile.close()
		modulefile = open(templatedir + "/module.html","r")
		moduledata = modulefile.read()
		modulefile.close()
		intlistfile = open(templatedir + "/int_list.html", "r")
		intlistdata = intlistfile.read()
		intlistfile.close()
	except:
		error("Could not open templates")


	try:
		os.chdir(dir)
	except:
		error("Could not chdir to target directory")	


#arg, i have to go through this dom tree ahead of time to build up the menus
	module_list = {}
	for node in doc.getElementsByTagName("module"):
                mod_name = mod_layer = interface_buf = ''

		mod_name = node.attributes.items()[0][1]
		mod_layer = node.parentNode.attributes.items()[0][1]

		for desc in node.getElementsByTagName("summary"):
			if desc.parentNode == node and desc:
				mod_summary = format_html_desc(desc)
		if not module_list.has_key(mod_layer):
			module_list[mod_layer] = {}

		module_list[mod_layer][mod_name] = mod_summary

#generate index pages
	main_content_buf = ''
	for mod_layer,modules in module_list.iteritems():
		menu = gen_doc_menu(mod_layer, module_list)

		menu_args = { "menulist" : menu,
			      "mod_layer" : mod_layer }
		menu_tpl = pyplate.Template(menudata)
		menu_buf = menu_tpl.execute_string(menu_args)

		content_tpl = pyplate.Template(indexdata)
		content_buf = content_tpl.execute_string(menu_args)

		main_content_buf += content_buf

		body_args = { "menu" : menu_buf,
			      "content" : content_buf }
	
		index_file = mod_layer + ".html"
		index_fh = open(index_file, "w")
		body_tpl = pyplate.Template(bodydata)
		body_tpl.execute(index_fh, body_args)
		index_fh.close()	

	menu = gen_doc_menu(None, module_list)
	menu_args = { "menulist" : menu,
		      "mod_layer" : None }
	menu_tpl = pyplate.Template(menudata)
	menu_buf = menu_tpl.execute_string(menu_args)

	body_args = { "menu" : menu_buf,
		      "content" : main_content_buf }

	index_file = "index.html"
	index_fh = open(index_file, "w")
	body_tpl = pyplate.Template(bodydata)
	body_tpl.execute(index_fh, body_args)
	index_fh.close()
#now generate the individual module pages

	all_interfaces = []
	for node in doc.getElementsByTagName("module"):
                mod_name = mod_layer = mod_desc = interface_buf = ''

		mod_name = node.attributes.items()[0][1]
		mod_layer = node.parentNode.attributes.items()[0][1]

		for desc in node.getElementsByTagName("summary"):
			if desc.parentNode == node:
				mod_summary = format_html_desc(desc)
		for desc in node.getElementsByTagName("desc"):
			if desc.parentNode == node:
				mod_desc = format_html_desc(desc)

		interfaces = []
		for interface in node.getElementsByTagName("interface"):
			interface_parameters = []
			interface_desc = interface_secdesc = interface_summary = None
			for i,v in interface.attributes.items():
				interface_name = v
			for desc in interface.getElementsByTagName("desc"):
				interface_desc = format_html_desc(desc)
			for desc in interface.getElementsByTagName("secdesc"):
				if desc:
					interface_secdesc = format_html_desc(desc)
			for desc in interface.getElementsByTagName("summary"):
				interface_summary = format_html_desc(desc)
			
			for args in interface.getElementsByTagName("param"):
				paramdesc = args.firstChild.data
				paramname = None
				paramopt = "No"
				for name,val in args.attributes.items():
					if name == "name":
						paramname = val
					if name == "optional":
						if val == "true":
							paramopt = "yes"
				parameter = { "name" : paramname,
					      "desc" : paramdesc,
					      "optional" : paramopt }
				interface_parameters.append(parameter)
			interfaces.append( { "interface_name" : interface_name,
					   "interface_summary" : interface_summary,
					   "interface_desc" : interface_desc,
					   "interface_parameters" : interface_parameters,
					   "interface_secdesc" : interface_secdesc })
			#all_interfaces is for the main interface index with all interfaces
			all_interfaces.append( { "interface_name" : interface_name,
					   "interface_summary" : interface_summary,
					   "interface_desc" : interface_desc,
					   "interface_parameters" : interface_parameters,
					   "interface_secdesc" : interface_secdesc,
					   "mod_name": mod_name,
					   "mod_layer" : mod_layer })
		interfaces.sort(int_cmp)	
		interface_tpl = pyplate.Template(intdata)
		interface_buf = interface_tpl.execute_string({"interfaces" : interfaces})
	
		menu = gen_doc_menu(mod_layer, module_list)

		menu_tpl = pyplate.Template(menudata)
		menu_buf = menu_tpl.execute_string({ "menulist" : menu })

		module_args = { "mod_layer" : mod_layer,
			      "mod_name" : mod_name,	
			      "mod_summary" : mod_summary,
			      "mod_desc" : mod_desc,
			      "interfaces" : interface_buf }

		module_tpl = pyplate.Template(moduledata)
		module_buf = module_tpl.execute_string(module_args)

		body_args = { "menu" : menu_buf,
			      "content" : module_buf }
			  
		module_file = mod_layer + "_" + mod_name + ".html"
		module_fh = open(module_file, "w")
		body_tpl = pyplate.Template(bodydata)
		body_tpl.execute(module_fh, body_args)
		module_fh.close()

		#and last build the interface index
	
		menu = gen_doc_menu(None, module_list)
		menu_args = { "menulist" : menu,
			      "mod_layer" : None }
		menu_tpl = pyplate.Template(menudata)
		menu_buf = menu_tpl.execute_string(menu_args)
	
		all_interfaces.sort(int_cmp)
		interface_tpl = pyplate.Template(intlistdata)
		interface_buf = interface_tpl.execute_string({"interfaces" : all_interfaces})
		int_file = "interfaces.html"
		int_fh = open(int_file, "w")
		body_tpl = pyplate.Template(bodydata)

		body_args = { "menu" : menu_buf, 
			      "content" : interface_buf }

		body_tpl.execute(int_fh, body_args)
		int_fh.close()

def error(error):
        sys.stderr.write("%s exiting for: " % sys.argv[0])
        sys.stderr.write("%s\n" % error)
        sys.stderr.flush()
        sys.exit(1)

def usage():
	sys.stdout.write("%s [-tmdT] -x <xmlfile>\n\n" % sys.argv[0])
	sys.stdout.write("Options:\n")
	sys.stdout.write("-t --tunables	<file>		--	write tunable config to <file>\n")
	sys.stdout.write("-m --modules <file>		--	write module config to <file>\n")
	sys.stdout.write("-d --docs <dir>		--	write interface documentation to <dir>\n")
	sys.stdout.write("-x --xml <file>		--	filename to read xml data from\n")
	sys.stdout.write("-T --templates <dir>		--	template directory for documents\n")

try:
	opts, args = getopt.getopt(sys.argv[1:], "t:m:d:x:T:", ["tunables","modules","docs","xml", "templates"])
except getopt.GetoptError:
	usage()
	sys.exit(1)

tunables = modules = docsdir = None
templatedir = "templates/"
xmlfile = "policy.xml"

for opt, val in opts:
	if opt in ("-t", "--tunables"):
		tunables = val
	if opt in ("-m", "--modules"):
		modules = val
	if opt in ("-d", "--docs"):
		docsdir = val
	if opt in ("-x", "--xml"):
		xmlfile = val
	if opt in ("-T", "--templates"):
		templatedir = val

doc = read_policy_xml(xmlfile)
		
if tunables:
	try:
		conf = open(tunables, 'w')
	except:
		error("Could not open tunables file for writing")
	gen_tunable_conf(doc, conf)
	conf.close()


if modules:
	try:
		conf = open(modules, 'w')
	except:
		error("Could not open modules file for writing")
	gen_module_conf(doc, conf)
	conf.close()

if docsdir: 
	gen_docs(doc, docsdir, templatedir)
