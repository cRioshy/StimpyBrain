"""Small stable architecture graph; raw observations are intentionally excluded."""
def build_graph():
    nodes=[
      {"id":"stimpy","label":"StimpyBrain","group":"stimpy","importance":1.0},
      {"id":"pando","label":"PandorickKi","group":"pandorick","importance":.7},
      {"id":"pando_api","label":"Pandorick Read-only API","group":"pandorick","importance":.8},
      {"id":"adapter","label":"Observation Adapter","group":"stimpy","importance":.8},
      {"id":"store","label":"Observation Store","group":"stimpy","importance":.9},
      {"id":"memory","label":"Memory","group":"stimpy","importance":.9},
      {"id":"learning","label":"Pattern Learning","group":"stimpy","importance":.7},
      {"id":"workflow","label":"Workflow Gate","group":"stimpy","importance":.9},
      {"id":"insight","label":"Stimpy Insight","group":"stimpy","importance":.6},
      {"id":"graph","label":"Stimpy Knowledge Graph","group":"stimpy","importance":.7},
      {"id":"api","label":"Stimpy Read-only API","group":"stimpy","importance":.8}]
    raw=[("pando","exposes_read_only","pando_api"),("pando_api","observed_by","adapter"),("adapter","stores_in","store"),("store","feeds","memory"),("store","evaluated_by","workflow"),("memory","supports","learning"),("workflow","produces","insight"),("learning","builds","graph"),("stimpy","uses","memory"),("stimpy","evaluates_with","workflow"),("stimpy","exposes","api")]
    return {"cluster":"StimpyBrain","nodes":nodes,"edges":[{"source":a,"relation":r,"target":b,"weight":1.0} for a,r,b in raw]}
