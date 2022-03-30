import ipdb

import logging
from typing import cast, List, Tuple, Dict
from .interpreter_utils import SPEAKERLOOK
from droidlet.memory.memory_nodes import (
    LocationNode,
    PlayerNode,
    ReferenceObjectNode,
    SelfNode,
    TaskNode,
)
from droidlet.memory.craftassist.mc_memory_nodes import InstSegNode
from .interpret_location import interpret_relative_direction
from .interpret_filters import interpret_selector
from droidlet.base_util import euclid_dist, number_from_span, T, XYZ
from droidlet.shared_data_structs import ErrorWithResponse, NextDialogueStep
from droidlet.dialog.dialogue_task import ClarifyDLF

DISALLOWED_REF_OBJS = (LocationNode, SelfNode, PlayerNode)
CC1_SEARCH_RADIUS = 15


def clarify_reference_objects(interpreter, speaker, d, candidate_mems, num_refs):
    ipdb.set_trace(context=5)

    # Decide what clarification class we're in
    if num_refs < 1:
        logging.error("There appear to be no references in the command to clarify, debug")
        raise ErrorWithResponse("I don't know what you're referring to")
    elif len(candidate_mems) == 0:
        clarification_class = "REF_NO_MATCH"
        dlf = cc1_to_dlf(interpreter, speaker, d, clarification_class)

        # extend the dialogue task class to a new clarification class that launches subtasks based on its status
        # problem: how to gracefully launch that first task and come back after?

        task_egg = {"class": ClarifyDLF, "task_data": {"dlf": dlf}}
        print(task_egg)
        cmemid = TaskNode.create(interpreter.memory, task_egg)
        interpreter.memory.add_triple(
            subj=cmemid,
            pred_text="dlf_clarification",
            obj=interpreter.memid,  # TODO Is this right???
        )
        raise NextDialogueStep()  # TODO what does this do?

    elif num_refs > len(candidate_mems):
        clarification_class = "REF_TOO_FEW"
        # TODO Build out CC2
    else:
        clarification_class = "REF_TOO_MANY"
        # TODO Build out CC3


def cc1_to_dlf(interpreter, speaker, d, clarification_class):
    # No reference objects found, expand search and ask for clarification
    clarification_query = "SELECT MEMORY FROM ReferenceObject WHERE x>-1000"
    _, clarification_ref_obj_mems = interpreter.memory.basic_search(clarification_query)
    objects = [x for x in clarification_ref_obj_mems if not isinstance(x, DISALLOWED_REF_OBJS)]
    mems = sort_by_closest(
        interpreter,
        speaker,
        objects,
        d,
        CC1_SEARCH_RADIUS,
    )
    if len(mems) == 0:
        raise ErrorWithResponse("I don't know what you're referring to")
    else:
        # Build the matchind dialog DLF
        action = retrieve_action_dict(interpreter, d)
        if not action:
            logging.error(
                "Unable to retrieve a matching action dictionary from top level logical form."
            )
            raise ErrorWithResponse("I don't know what you're referring to")

        dlf = build_dlf(clarification_class, mems, action)
        return dlf


def retrieve_action_dict(interpreter, d):
    action = False
    potential_actions = interpreter.logical_form["action_sequence"]
    for pa in potential_actions:
        if pa["reference_object"] == d:
            action = pa
    return action


def build_dlf(cc, candidates, action):
    dlf = {
        "dialogue_type": "CLARIFICATION",
        "action": action,
        "class": {
            "error_type": cc,
            "candidates": [mem.memid for mem in candidates],
        },
    }
    return dlf


def sort_by_closest(
    interpreter, speaker, candidates: List[T], d: Dict, all_proximity=10, loose=False
) -> List[T]:
    """Sort a list of candidate reference_object mems by distance to ref_loc
    within all_proximity
    Returns a list of mems
    """
    filters_d = d.get("filters")
    assert filters_d is not None, "no filters: {}".format(d)
    default_loc = getattr(interpreter, "default_loc", SPEAKERLOOK)
    location = filters_d.get("selector", {}).get("location", default_loc)
    reldir = location.get("relative_direction")
    location_filtered_candidates = []

    mems = interpreter.subinterpret["reference_locations"](interpreter, speaker, location)
    steps, reldir = interpret_relative_direction(interpreter, d)
    ref_loc, _ = interpreter.subinterpret["specify_locations"](
        interpreter, speaker, mems, steps, reldir
    )
    location_filtered_candidates = [
        c for c in candidates if euclid_dist(c.get_pos(), ref_loc) <= all_proximity
    ]
    location_filtered_candidates.sort(key=lambda c: euclid_dist(c.get_pos(), ref_loc))

    mems = location_filtered_candidates
    if location_filtered_candidates:  # could be [], if so will return []
        default_selector_d = {"return_quantity": "ALL"}
        # default_selector_d = {"location": {"location_type": "SPEAKER_LOOK"}}
        selector_d = filters_d.get("selector", default_selector_d)
        S = interpret_selector(interpreter, speaker, selector_d)
        if S:
            memids, _ = S(
                [c.memid for c in location_filtered_candidates],
                [None] * len(location_filtered_candidates),
            )
            mems = [interpreter.memory.get_mem_by_id(m) for m in memids]
        else:
            pass
            # FIXME, warn/error here; mems is still the candidates

    return mems
