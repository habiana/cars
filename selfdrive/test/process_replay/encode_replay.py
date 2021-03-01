#!/usr/bin/env python3
import os
import sys
import time
from tqdm import trange

import cereal.messaging as messaging
from tools.lib.framereader import FrameReader

from common.hardware import ANDROID
if ANDROID:
  os.environ['QCOM_REPLAY'] = "1"

FPS = 20
SUBSEGMENT_LEN = 6
TEST_FN = "/data/a74b011b32b51b56_2020-11-30--08-34-18--1--fcamera.hevc"
# TEST_FN_2 = "/data/a74b011b32b51b56_2020-11-30--08-34-18--2--fcamera.hevc"

def get_fr_frame(fr, idx):
  return fr.get(idx, pix_fmt="rgb_24")[0]

if __name__ == "__main__":
  import selfdrive.manager as manager

  pre_cache = "--cache" in sys.argv
  subloop = "--subloop" in sys.argv

  if subloop:
    os.environ['LOGGERD_TEST'] = "1"
    os.environ['LOGGERD_SEGMENT_LENGTH'] = str(SUBSEGMENT_LEN)

  manager.prepare_managed_process("loggerd")
  manager.prepare_managed_process("camerad")

  manager.start_managed_process("loggerd")
  manager.start_managed_process("camerad")
  time.sleep(3)

  pm = messaging.PubMaster(['frame'])

  fr = FrameReader(TEST_FN)
  fcount = fr.frame_count

  if pre_cache:
    print("caching 1: %d" % fcount)
    for i in trange(fcount):
      if not os.path.isfile("/data/fcamcache/1_%d" % i):
        img_bgr = get_fr_frame(fr, i)[:, :, ::-1]
        with open("/data/fcamcache/1_%d" % i, "wb") as f:
          f.write(img_bgr.flatten().tobytes())

  t0 = 16506889393000
  idx = 0

  print("replaying %s, %d frames" % (TEST_FN, fcount))

  n = 1
  if subloop:
    fcount = FPS * SUBSEGMENT_LEN
    n = 1200 // fcount

  for _ in range(n):
    for i in trange(fcount):
      with open("/data/fcamcache/1_%d" % i, "rb") as f:
        d = f.read()

      dat = messaging.new_message('frame')
      dat.frame = {
        "image": d,
        "frameId": idx,
        "timestampEof": t0 + idx * 50000000,
      }
      pm.send('frame', dat)
      print("1-%d(%d) frame sent, at %d" % (idx, i, t0 + idx * 50000000))
      idx += 1
      if idx < 1:
        time.sleep(2)
      time.sleep(1/FPS)

  time.sleep(2)
  manager.kill_managed_process('loggerd')
  manager.kill_managed_process('camerad')
  print("finished")

