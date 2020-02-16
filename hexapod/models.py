import numpy as np
import plotly.graph_objects as go

# rotate about y, translate in x
def frame_yrotate_xtranslate(theta, x):
  theta = np.radians(theta)
  cos_theta = np.cos(theta)
  sin_theta = np.sin(theta)

  return np.array([
    [cos_theta, 0, sin_theta, x],
    [0, 1, 0, 0],
    [-sin_theta, 0, cos_theta, 0],
    [0, 0, 0, 1]
  ])

# rotate about z, translate in x and y
def frame_zrotate_xytranslate(theta, x, y):
  theta = np.radians(theta)
  cos_theta = np.cos(theta)
  sin_theta = np.sin(theta)

  return np.array([
    [cos_theta, -sin_theta, 0, x],
    [sin_theta, cos_theta, 0, y],
    [0, 0, 1, 0],
    [0, 0, 0, 1]
  ])

class Point:
  def __init__(self, x, y, z):
    self.x = x
    self.y = y
    self.z = z

  def get_point_wrt(self, reference_frame):
    # given frame_ab which is the pose of frame_b wrt frame_a
    # given a point as defined wrt to frame_b
    # return point defined wrt to frame a
    p = np.array([self.x, self.y, self.z, 1])
    p = np.matmul(reference_frame, p)
    return Point(p[0], p[1], p[2])

# -------------
# LINKAGE
# -------------
# Neutral position of the linkages (alpha=0, beta=0, gamma=0)
# note that at neutral position:
#  link b and link c are perpendicular to each other
#  link a and link b form a straight line
#  link a coincide with x axis
#
# alpha - the able linkage a makes with x_axis about z axis
# beta - the angle that linkage a makes with linkage b
# gamma - the angle that linkage c make with the line perpendicular to linkage b
#
#
# MEASUREMENTS
#
#  |--- a--------|--b--|
#  |=============|=====| p2 -------
#  p0            p1    |          |
#                      |          |
#                      |          c
#                      |          |
#                      |          |
#                      | p3  ------
#
#  z axis
#  |
#  |
#  |------- x axis
# origin
#
#
# ANGLES beta and gamma
#                /
#               / beta
#         ---- /* ---------
#        /    //\\        \
#       b    //  \\        \
#      /    //    \\        c
#     /    //beta  \\        \
# *=======* ---->   \\        \
# |---a---|          \\        \
#                     *-----------
#
# |--a--|---b----|
# *=====*=========* -------------
#               | \\            \
#               |  \\            \
#               |   \\            c
#               |    \\            \
#               |gamma\\            \
#               |      *----------------
#
class Linkage:
  def __init__(self, a, b, c, alpha=0, beta=0, gamma=0, new_x_axis=0, new_origin=Point(0, 0, 0)):
    self.store_linkage_attributes(a, b, c, new_x_axis, new_origin)
    self.save_new_pose(alpha, beta, gamma)

  def store_linkage_attributes(self, a, b, c, new_x_axis, new_origin):
    self._a = a
    self._b = b
    self._c = c
    self._new_origin = new_origin
    self._new_x_axis = new_x_axis

  def save_new_pose(self, alpha, beta, gamma):
    self._alpha = alpha
    self._beta = beta
    self._gamma = gamma

    # frame_ab is the pose of frame_b wrt frame_a
    frame_01 = frame_yrotate_xtranslate(theta=-self._beta, x=self._a)
    frame_12 = frame_yrotate_xtranslate(theta=90-self._gamma, x=self._b)
    frame_23 = frame_yrotate_xtranslate(theta=0, x=self._c)

    frame_02 = np.matmul(frame_01, frame_12)
    frame_03 = np.matmul(frame_02, frame_23)
    new_frame = frame_zrotate_xytranslate(self._new_x_axis + self._alpha, self._new_origin.x, self._new_origin.y)

    # find points wrt to body contact point
    p0 = Point(0, 0, 0)
    p1 = p0.get_point_wrt(frame_01)
    p2 = p0.get_point_wrt(frame_02)
    p3 = p0.get_point_wrt(frame_03)

    # find points wrt to center of gravity
    self.p0 = self._new_origin
    self.p1 = p1.get_point_wrt(new_frame)
    self.p2 = p2.get_point_wrt(new_frame)
    self.p3 = p3.get_point_wrt(new_frame)

  def change_pose(self, alpha=None, beta=None, gamma=None):
    alpha = alpha or self._alpha
    beta = beta or self._beta
    gamma = gamma or self._gamma
    self.save_new_pose(alpha, beta, gamma)

# MEASUREMENTS f, s, and m
#
#       |-f-|
#       *---*---*--------
#      /    |    \     |
#     /     |     \    s
#    /      |      \   |
#   *------cog------* ---
#    \      |      /|
#     \     |     / |
#      \    |    /  |
#       *---*---*   |
#           |       |
#           |---m---|
#
#    y axis
#    ^
#    |
#    |
#    ----> x axis
#  cog (origin)
#
#
# Relative x-axis, for each attached linkage
#
#         x2          x1
#          \         /
#           *---*---*
#          /    |    \
#         /     |     \
#        /      |      \
#  x3 --*------cog------*-- x0
#        \      |      /
#         \     |     /
#          \    |    /
#           *---*---*
#          /         \
#         x4         x5
#
class Hexagon:
  def __init__(self, f, m, s):
    self.f = f
    self.m = m
    self.s = s

    self.cog = Point(0, 0, 0)
    self.head = Point(0, s, 0)
    self.vertices = [
      Point(m, 0, 0),
      Point(f, s, 0),
      Point(-f, s, 0),
      Point(-m, 0, 0),
      Point(-f, -s, 0),
      Point(f, -s, 0),
    ]

    self.new_x_axes = [
      0, 45, 135, 180, 225, 315
    ]

class VirtualHexapod:
  def __init__(self, a=0, b=0, c=0, f=0, m=0, s=0):
    self.linkage_measurements = [a, b, c]
    self.body_measurements = [f, m, s]
    self.body = Hexagon(f, m, s)
    self.store_neutral_legs(a, b, c)

  def store_neutral_legs(self, a, b, c):
    self.legs = []
    for point, theta in zip(self.body.vertices, self.body.new_x_axes):
      linkage = Linkage(a, b, c, new_x_axis=theta, new_origin=point)
      self.legs.append(linkage)