# -*- coding: utf-8 -*-
"""
以LTP平台分词技术为基础，辅以大词林的分词程序
"""

__author__ = "tianwen jiang"

import os

from lxml import etree
from pyltp import Segmentor, Postagger, NamedEntityRecognizer

# model path
MODELDIR="/data/ltp/ltp-models/3.3.0/ltp_data"
#MODELDIR="/home/twjiang/01.lab/ltp_model/3.3.0/ltp_data"
print "正在加载LTP模型... ..."
segmentor = Segmentor()
segmentor.load(os.path.join(MODELDIR, "cws.model"))
postagger = Postagger()
postagger.load(os.path.join(MODELDIR, "pos.model"))
recognizer = NamedEntityRecognizer()
recognizer.load(os.path.join(MODELDIR, "ner.model"))
print "模型加载完毕."
print "正在加载大词林实体词库... ..."
bigcilin_file = open("/users1/twjiang/03.data/entitys_bigcilin.txt")
bigcilin = []

line = bigcilin_file.readline()
while line:
    entity = line.strip()
    bigcilin.append(entity)
    line = bigcilin_file.readline()
bigcilin_file.close()

print "大词林实体词库加载完毕: 已加载%d实体" % (len(bigcilin))

piece_size = 3
limit_len = 3

def segment_sentence(sentence, use_bigcilin = 1, must_entity=None):
    """
    对给定的中文句子进行分词
    Args:
        sentence: 要分词的中文语句
        is_use_bigcilin: 是否使用大词林辅助分词
    Return: 
        words: 分词结果list
        entitys: 句子中在大词林中的开放域实体list
    """
    words = []
    entitys = set()
    ltp_words = segmentor.segment(sentence)
    
    if use_bigcilin == 1:
        words = ltp_words
        stop_words = []
        stopwords_file = open("/users1/twjiang/03.data/stopwords.dic")
        line = stopwords_file.readline()
        while line:
            stop_word = line.strip()
            stop_words.append(stop_word)
            line = stopwords_file.readline()
        stopwords_file.close()

        ltp_postags = postagger.postag(ltp_words)
        begin_position = 0
        while begin_position < len(ltp_words):
            if ltp_words[begin_position] in stop_words:
                begin_position += 1
                continue
            if ltp_postags[begin_position] in ['c', 'm', 'e', 'p', 'u', 'v', 'wp', 'ws']:
                begin_position += 1
                continue
                    
            for bia in range(piece_size):
                temp_word = "".join(ltp_words[begin_position:begin_position+piece_size-bia])
                #print temp_word
                if temp_word == must_entity:
                    entitys.add(temp_word)
                if temp_word in bigcilin:
                    #print "#####"+temp_word
                    if len(temp_word)/3 >= limit_len and temp_word.decode('utf-8')[-1] != u"的":
                        entitys.add(temp_word)
                    begin_position += piece_size-bia
                    break
                else:
                    if bia == piece_size-1:
                        begin_position += 1
                        break
                    continue
            
    return words, entitys

def nerecognize_xml_file(in_file_name, out_file_name, use_bigcilin = 1):
    """
    对文件中的文本进行实体识别
    Args:
        in_file_name: 输入文件
        out_file_name: 输出文件
    Return:
    """
    named_entitys = set()

    docs_root = etree.parse(in_file_name).getroot()
    out_docs_root = etree.Element("docs")
    for each_doc in docs_root:  # 遍历每个doc
        out_doc_element = etree.SubElement(out_docs_root, "doc")
        out_doc_element.attrib["name"] = each_doc.attrib["name"]
        must_entity = each_doc.attrib["name"].encode('utf-8')
        out_doc_element.attrib["url"] = each_doc.attrib["url"]
        out_doc_element.attrib["id"] = each_doc.attrib["id"]
        out_doc_element.attrib["baike_id"] = each_doc.attrib["baike_id"]
        out_doc_element.attrib["time"] = each_doc.attrib["time"]
        for each_par in each_doc:
            out_par_element = etree.SubElement(out_doc_element, "par")
            sentences_list = []
            acculen_list = []
            sentences_lbia_list = []
            acculen = 0
            acculen_lbia = 0
            try:
                for element in each_par:
                    if element.tag == "text":  # 也可以判断tag来访问
                        text = element.text.encode('utf-8')
                        #out_text_element = etree.SubElement(out_par_element, "text")
                        #out_text_element.text = element.text
                        text = text.replace("。","。\n").replace("！","！\n").replace("？","？\n")
                        sentences = text.split("\n")
                        for sentence in sentences:
                            sentence = sentence.rstrip()
                            len1 = len(sentence.decode('utf-8'))
                            sentence = sentence.lstrip()
                            len2 = len(sentence.decode('utf-8'))
                            acculen_lbia += len1-len2
                            sentences_lbia_list.append(acculen_lbia)
                            if sentence == '':
                                continue
                            u_sentence = sentence.decode('utf-8')
                            out_sentence_element = etree.SubElement(out_par_element, "sentence")
                            out_s_text_element = etree.SubElement(out_sentence_element, "s_text")
                            out_s_text_element.text = u_sentence
                            acculen += len(u_sentence)
                            print '[sentence]:',sentence
                            words, entitys = segment_sentence(sentence, use_bigcilin, must_entity)
                            postags = postagger.postag(words)
                            netags = recognizer.recognize(words, postags)
                            for i in range(len(netags)):
                                a_ne = ''
                                if netags[i][0] == 'B':
                                    j = i
                                    while True:
                                        a_ne += words[j]
                                        if netags[j][0] == 'E':
                                            break
                                        j +=1
                                    if a_ne not in named_entitys:
                                        named_entitys.add(a_ne)
                                        a_ne = a_ne.decode('utf-8')
                                        out_e_element = etree.SubElement(out_sentence_element, "e")
                                        try:
                                            out_e_element.attrib["start"] = str(u_sentence.index(a_ne))
                                        except:
                                            out_e_element.attrib["start"] = str(u_sentence.index(words[i].decode('utf-8')))
                                        out_e_element.attrib["length"] = str(len(a_ne))
                                        out_e_element.attrib["baike_id"] = u"NULL"
                                        out_e_element.attrib["type"] = netags[i][2:].decode('utf-8')
                                        out_e_element.text = a_ne
                                if netags[i][0] == 'S':
                                    a_ne = words[i]
                                    if a_ne not in named_entitys:
                                        named_entitys.add(a_ne)
                                        a_ne = a_ne.decode('utf-8')
                                        out_e_element = etree.SubElement(out_sentence_element, "e")
                                        out_e_element.attrib["start"] = str(u_sentence.index(a_ne))
                                        out_e_element.attrib["length"] = str(len(a_ne))
                                        out_e_element.attrib["baike_id"] = u"NULL"
                                        out_e_element.attrib["type"] = netags[i][2:].decode('utf-8')
                                        out_e_element.text = a_ne
                            for ne in entitys:
                                u_ne = ne.decode('utf-8')
                                out_e_element = etree.SubElement(out_sentence_element, "e")
                                out_e_element.attrib["start"] = str(u_sentence.index(u_ne))
                                out_e_element.attrib["length"] = str(len(u_ne))
                                out_e_element.attrib["baike_id"] = u"NULL"
                                out_e_element.text = u_ne
                                out_e_element.attrib["type"] = "bigcilin"
                                if ne == must_entity:
                                    out_e_element.attrib["type"] = "name"
                            sentences_list.append(out_sentence_element)
                            acculen_list.append(acculen)
                            named_entitys = set()
                    if element.tag == "a":
                        a_start = int(element.attrib["start"])
                        index = 0
                        while a_start >= acculen_list[index]:
                            index += 1
                        if index > 0:
                            a_start -= acculen_list[index-1]
                        out_e_element = etree.SubElement(sentences_list[index], "e")
                        out_e_element.attrib["start"] = str(a_start-sentences_lbia_list[index])
                        out_e_element.attrib["length"] = element.attrib["length"]
                        out_e_element.attrib["baike_id"] = element.attrib["baike_id"]
                        out_e_element.attrib["type"] = "href"
                        out_e_element.text = element.text
                for i in range(len(sentences_list)):
                    e_element_list = []
                    for j in range(1,len(sentences_list[i])):
                        e_element_list.append(E_element(int(sentences_list[i][j].attrib["start"]), int(sentences_list[i][j].attrib["length"]),
                                                       sentences_list[i][j].attrib["baike_id"], sentences_list[i][j].attrib["type"], 
                                                        sentences_list[i][j].text))
                    e_element_list_sorted = sorted(e_element_list, key=lambda e_element:(e_element.start,e_element.length))
                    for j in range(len(e_element_list_sorted)):
                        sentences_list[i][j+1].attrib["start"] = str(e_element_list_sorted[j].start)
                        sentences_list[i][j+1].attrib["length"] = str(e_element_list_sorted[j].length)
                        sentences_list[i][j+1].attrib["baike_id"] = e_element_list_sorted[j].baike_id
                        sentences_list[i][j+1].attrib["type"] = e_element_list_sorted[j].type
                        sentences_list[i][j+1].text = e_element_list_sorted[j].text
                for i in range(len(sentences_list)):
                    s = sentences_list[i]
                    for j in range(len(s)-1,1,-1):
                        if s[j-1].attrib["start"]==s[j].attrib["start"] and s[j-1].attrib["length"]==s[j].attrib["length"]:
                            s[j-1].attrib["type"] += "|"+s[j].attrib["type"]
                            if s[j-1].attrib["baike_id"]==u"NULL":
                                s[j-1].attrib["baike_id"] = s[j].attrib["baike_id"]
                                s[j].xpath("..")[0].remove(s[j])
            except:
                continue
    tree = etree.ElementTree(out_docs_root)
    tree.write(out_file_name, pretty_print=True, xml_declaration=True, encoding='utf-8')

class E_element(object):
    def __init__(self, start, length, baike_id, type, text):
        self.start = start
        self.length = length
        self.baike_id = baike_id
        self.type = type
        self.text = text
