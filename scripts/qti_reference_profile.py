"""Bounded educational QTI 3 single-choice XML example; not a general importer."""
from dataclasses import dataclass
import re
import xml.etree.ElementTree as ET

NS = "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
TEMPLATE = "https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
MAX_BYTES = 65536
ET.register_namespace("", NS)

@dataclass(frozen=True)
class ChoiceItem:
    identifier: str
    title: str
    language: str
    prompt: str
    choices: tuple[tuple[str, str], ...]
    correct: str

def tag(name):
    return "{"+NS+"}qti-"+name

def validate(item):
    identifiers = [item.identifier, *(k for k,_ in item.choices)]
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,63}", k) for k in identifiers):
        raise ValueError("unsupported identifier")
    keys = [k for k,_ in item.choices]
    if not 2 <= len(keys) <= 20 or len(set(keys)) != len(keys) or item.correct not in keys:
        raise ValueError("invalid choices or key")
    if not re.fullmatch(r"[a-zA-Z]{2,8}(?:-[a-zA-Z0-9]{1,8})*",item.language):
        raise ValueError("unsupported language tag")
    if any(not isinstance(t,str) or not t.strip() or len(t)>8000 or
           any(ord(c)<32 and c not in "\t\n\r" for c in t)
           for t in (item.title,item.prompt,*(v for _,v in item.choices))):
        raise ValueError("invalid text")

def export_item(item):
    validate(item)
    root=ET.Element(tag("assessment-item"), {"identifier":item.identifier,"title":item.title,
        "adaptive":"false","time-dependent":"false",XML_LANG:item.language})
    def add(parent,name,attrs=None,text=None):
        node=ET.SubElement(parent,tag(name),attrs or {})
        node.text=text
        return node
    response=add(root,"response-declaration",{"identifier":"RESPONSE","cardinality":"single","base-type":"identifier"})
    correct=add(response,"correct-response")
    add(correct,"value",text=item.correct)
    add(root,"outcome-declaration",{"identifier":"SCORE","cardinality":"single","base-type":"float"})
    body=add(root,"item-body")
    interaction=add(body,"choice-interaction",{"response-identifier":"RESPONSE","shuffle":"false","max-choices":"1"})
    add(interaction,"prompt",text=item.prompt)
    for key,text in item.choices:
        add(interaction,"simple-choice",{"identifier":key},text)
    add(root,"response-processing",{"template":TEMPLATE})
    raw=ET.tostring(root,encoding="utf-8",xml_declaration=True)
    if len(raw)>MAX_BYTES:
        raise ValueError("XML exceeds profile limit")
    return raw

def shape(node):
    # Accept indentation and attribute ordering, not extra content or mixed markup.
    return (node.tag,tuple(sorted(node.attrib.items())),
            node.text if len(node)==0 else (node.text or "").strip(),
            (node.tail or "").strip(),tuple(shape(child) for child in node))

def import_item(raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_BYTES or b"\x00" in raw:
        raise ValueError("unsupported XML bytes")
    try:
        decoded=raw.decode("utf-8")
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)|<!--|<\?(?!xml\s)",decoded,re.I):
            raise ValueError("unsupported XML declaration or markup")
        # Restrict encodings so byte guards and parser interpretation agree.
        decl=re.match(r"\ufeff?<\?xml\s+([^?]+)\?>",decoded)
        if decl:
            enc=re.search(r"encoding\s*=\s*['\"]([^'\"]+)['\"]",decl[1],re.I)
            if enc and enc[1].lower() not in {"utf-8","utf8"}:
                raise ValueError("unsupported XML encoding")
        root=ET.fromstring(decoded)
        if root.tag!=tag("assessment-item"):
            raise ValueError("unsupported root or QTI version")
        response=root.find(tag("response-declaration"))
        body=root.find(tag("item-body"))
        interaction=body.find(tag("choice-interaction"))
        item=ChoiceItem(root.attrib["identifier"],root.attrib["title"],root.attrib[XML_LANG],
            interaction.find(tag("prompt")).text,
            tuple((c.attrib["identifier"],c.text) for c in interaction.findall(tag("simple-choice"))),
            response.find(tag("correct-response")).find(tag("value")).text)
        canonical=ET.fromstring(export_item(item))
        if shape(root)!=shape(canonical):
            raise ValueError("unsupported interaction, metadata or scoring; no lossy import")
        return item
    except (ET.ParseError, UnicodeError, KeyError, AttributeError, TypeError, RecursionError) as exc:
        raise ValueError("invalid or unsupported QTI profile") from exc
