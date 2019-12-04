import os
import time
import math
import numpy as np
import select
import argparse
import subprocess
import collections
from . import logger
from .config import global_config as c
from .linalg_helpers import *
from .tracked_user import WorldTrackedUser


l = logger.getChild("tracker")

PREFIX = b"HT! "
HAND_DATA = b"HAND DATA: "
SEP_CHAR = b"|"
FRAME_END = b"FRAME END"

DEG_TO_RAD = (2 * math.pi) / 360

class Tracker(object):
    def __init__(self, tracker, working_directory):
        self.tracker = tracker
        self.working_directory = working_directory
        self.proc = None

    @staticmethod
    def decode(payload):
        def _parse_coords(co):
            elements = co.strip().lstrip(b"(").rstrip(b")").replace(b" ", b"").split(b",")
            return pitch(point(*map(float, elements)), -c.tracker.CAMERA_PITCH * DEG_TO_RAD)
        parts = payload.split(SEP_CHAR)
        return WorldTrackedUser(int(parts[0]),
                                _parse_coords(parts[1]), # head
                                _parse_coords(parts[2]), # neck
                                _parse_coords(parts[3]), # torso
                                _parse_coords(parts[4]), # lshoulder
                                _parse_coords(parts[5]), # lelbow
                                _parse_coords(parts[6]), # lhand
                                _parse_coords(parts[7]), # rshoulder
                                _parse_coords(parts[8]), # relbow
                                _parse_coords(parts[9]), # rhand
                                _parse_coords(parts[10]), # lhip
                                _parse_coords(parts[11]), # lknee
                                _parse_coords(parts[12]), # lfoot
                                _parse_coords(parts[13]), # rhip
                                _parse_coords(parts[14]), # rknee
                                _parse_coords(parts[15]), # rfoot

    @staticmethod
    def flip_user(u):
        def _flip(p, center):
            x = -(p[0] - center[0]) + center[0]
            return point(x, p[1], p[2])

        h = _flip(u.head, u.torso)
        n = _flip(u.neck, u.torso)

        ls = _flip(u.right_shoulder, u.torso)
        le = _flip(u.right_elbow, u.torso)
        lh = _flip(u.right_hand, u.torso)

        rs = _flip(u.left_shoulder, u.torso)
        re = _flip(u.left_elbow, u.torso)
        rh = _flip(u.left_hand, u.torso)

        lhip = _flip(u.right_hip, u.torso)
        lk = _flip(u.right_knee, u.torso)
        lf = _flip(u.right_foot, u.torso)

        rhip = _flip(u.right_hip, u.torso)
        rk = _flip(u.right_knee, u.torso)
        rf = _flip(u.right_foot, u.torso)




        return WorldTrackedUser(user_id=u.user_id,
                                head=h, neck=n, torso=u.torso,
                                left_shoulder=ls, left_elbow=le, left_hand=lh,
                                right_shoulder=rs, right_elbow=re, right_hand=rh,
                                left_hip=lhip, left_knee=lk, left_foot=lf,
                                right_hip=rhip, right_knee=rk, right_foot=rf)

    def sync_stream(self):
        # After a long-running operation such as the TAS, a large amount of data
        # can build up in the proc.stdout buffer. `select` checks if data is available,
        # which allows us to skip past the data that has built up.
        # When select returns false, there is no more data available and we are back
        # to "real-time."
        while self.proc.stdout in select.select([self.proc.stdout], [], [], 0)[0]:
            self.proc.stdout.readline()

    def get_frame(self):
        users = {}
        while True:
            line = self.proc.stdout.readline().strip()
            if not line.startswith(PREFIX):
                continue
            line = line.replace(PREFIX, b"", 1)
            if line.startswith(HAND_DATA):
                u = self.decode(line.replace(HAND_DATA, b"", 1))
                users[u.user_id] = u
            elif line.startswith(FRAME_END):
                break
            else:
                l.error("invalid line: %r", line)
        return users.values()

    def stream(self):
        l.info("Starting fake stream to bypass bug")
        proc = subprocess.Popen([self.tracker], cwd=self.working_directory,
                                stdout=subprocess.PIPE)
        time.sleep(c.tracker.FAKE_DELAY_TIME)
        proc.kill()
        time.sleep(c.tracker.FAKE_DELAY_TIME)
        l.info("Beginning stream")
        self.proc = subprocess.Popen([self.tracker], cwd=self.working_directory,
                                     stdout=subprocess.PIPE)
        try:
            while True:
                users = self.get_frame()
                yield self.find_hand_angle(users)
        finally:
            l.warn("Killing process after exception")
            self.proc.kill()

    @staticmethod
    def filter_users_range(users):
        def _is_in_range(u):
            # Check that torso is not too far away (z-axis)
            if u.torso[2] > c.tracker.TORSO_MAX_DISTANCE:
                return False

            # Check that torso is not too close
            if u.torso[2] < c.tracker.TORSO_MIN_DISTANCE:
                return False

            # Check that torso is centered
            if abs(u.torso[0] - c.tracker.TORSO_CENTER) > c.tracker.TORSO_CENTER_TOLERANCE:
                return False

            return True

        return tuple(filter(_is_in_range, users))

    @classmethod
    def find_optimal_user(cls, users):
        def _is_valid(u):
            return True

        in_range = cls.filter_users_range(users)
        filtered = tuple(filter(_is_valid, in_range))
        l.debug("Filtered %d users to %d to %d" % (len(users), len(in_range), len(filtered)))
        if len(filtered) == 0:
            return None

        return sorted(filtered, key=lambda u: u.torso[2])[0]

    @classmethod
    def find_hand_angle(cls, users):
        u = cls.find_optimal_user(users)
        if u:
            delta = u.left_hand - u.right_hand
            return math.atan2(delta[1], delta[0])
        return None