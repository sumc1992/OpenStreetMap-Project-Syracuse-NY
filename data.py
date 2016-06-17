#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Data processing, cleaning and formating script for OpenStreetMap project
"""

import csv
import codecs
import re
import xml.etree.cElementTree as ET

import cerberus

import schema

OSM_PATH = 'syracuse_new-york.osm'

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements
    counter = 0
    ''' Case when element tag is node!!! '''

    if element.tag == 'node':
        # convert and format node attributes
        for field in node_attr_fields:
            node_attribs[field] = element.attrib[field]
        for tag in element.iter('tag'):
            holder = {}
            if PROBLEMCHARS.search(tag.attrib['k']):
                None
            elif tag.attrib['k'].find(':') == -1:
                holder['id'] = element.attrib['id']
                holder['value'] = tag.attrib['v']
                holder['key'] = tag.attrib['k']
                holder['type'] = default_tag_type
            else:
                position = tag.attrib['k'].find(':')
                np = position + 1
                holder['id'] = element.attrib['id']
                holder['value'] = tag.attrib['v']
                holder['key'] = tag.attrib['k'][np:1000]
                holder['type'] = tag.attrib['k'][0:position]
            if 'key' in holder.keys() and holder['key'] == 'street':
                holder['value'] = update_name(holder['value'])
            if 'key' in holder.keys() and holder['key'] == 'postcode':
                holder['value'] = update_zip(holder['value'])
            tags.append(holder)

        return {'node': node_attribs, 'node_tags': tags}
        ''' Case when element tag is 'way' '''
    elif element.tag == 'way':
        for field in way_attr_fields:
            way_attribs[field] = element.attrib[field]

        for tag in element.iter('tag'):
            holder = {}
            if PROBLEMCHARS.search(tag.attrib['k']):
                None
            elif tag.attrib['k'].find(':') == -1:
                holder['id'] = element.attrib['id']
                holder['value'] = tag.attrib['v']
                holder['key'] = tag.attrib['k']
                holder['type'] = default_tag_type
            else:
                position = tag.attrib['k'].find(':')
                np = position + 1
                holder['id'] = element.attrib['id']
                holder['value'] = tag.attrib['v']
                holder['key'] = tag.attrib['k'][np:1000]
                holder['type'] = tag.attrib['k'][0:position]
            if 'key' in holder.keys() and holder['key'] == 'street':
                holder['value'] = update_name(holder['value'])
            if 'key' in holder.keys() and holder['key'] == 'postcode':
                holder['value'] = update_zip(holder['value'])
            tags.append(holder)

        for node in element.iter('nd'):
            holder = {}
            holder['id'] = element.attrib['id']
            holder['node_id'] = node.attrib['ref']
            holder['position'] = counter
            way_nodes.append(holder)
            counter += 1
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def update_zip(zip_code):
    if len(zip_code) == 5:
        return zip_code
    else:
        return zip_code[0:5]

def update_name(name):
    # Only two street name abbreviations are found.
    mapping = { "St": "Street",
                "Courts": "Court"
                }
    # I could have used re function to catch the abbreviation and route number
    # But there are only 5 corrections to be made, i decided to go manually
    if name == 'James St':
        name = 'James Street'
    elif name == 'Presidental Courts':
        name = 'Presidential Court'
    elif name in ['New York 31', 'State Route 31', 'State Highway 31']:
        name = 'New York 31'
    elif name == 'State Route 298':
        name = 'New York 298'
    elif name == 'US Route 11':
        name = 'Route 11'
    return name

def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_strings = (
            "{0}: {1}".format(k, v if isinstance(v, str) else ", ".join(v))
            for k, v in errors.iteritems()
        )
        raise cerberus.ValidationError(
            message_string.format(field, "\n".join(error_strings))
        )


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])

process_map(OSM_PATH, validate = False)
