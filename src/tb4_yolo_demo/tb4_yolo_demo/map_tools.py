import argparse
import math
from pathlib import Path

import cv2
import numpy as np
import yaml

from .common import load_goals


class SavedMap:
    def __init__(self, filename):
        self.path = Path(filename)
        self.meta = yaml.safe_load(self.path.read_text())
        image = cv2.imread(str(self.path.parent / self.meta['image']), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError('Map image cannot be read')
        self.image = image
        self.resolution = float(self.meta['resolution'])
        self.origin = self.meta['origin']
        occupancy = image.astype(float) / 255.0
        if not self.meta.get('negate', 0):
            occupancy = 1.0 - occupancy
        self.free = occupancy < self.meta['free_thresh']
        self.occupied = occupancy > self.meta['occupied_thresh']
        padded = np.pad(self.free.astype(np.uint8), 1)
        self.clearance = cv2.distanceTransform(padded, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)[1:-1, 1:-1] * self.resolution
        self.wall_distance = cv2.distanceTransform((~self.occupied).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE) * self.resolution

    def pixel(self, x, y):
        dx, dy = x-self.origin[0], y-self.origin[1]
        c, s = math.cos(self.origin[2]), math.sin(self.origin[2])
        col = math.floor((c*dx+s*dy)/self.resolution)
        row = self.image.shape[0]-1-math.floor((-s*dx+c*dy)/self.resolution)
        return row, col

    def world(self, row, col):
        x = (col+.5)*self.resolution
        y = (self.image.shape[0]-row-.5)*self.resolution
        c,s = math.cos(self.origin[2]), math.sin(self.origin[2])
        return self.origin[0]+c*x-s*y, self.origin[1]+s*x+c*y

    def check(self, x, y, clearance):
        row, col = self.pixel(x, y)
        if not (0 <= row < self.image.shape[0] and 0 <= col < self.image.shape[1]):
            raise ValueError(f'Point ({x}, {y}) is outside map')
        distance = float(self.clearance[row, col])
        if not self.free[row, col] or distance < clearance:
            raise ValueError(f'Point ({x}, {y}): clearance={distance:.3f} m < {clearance:.3f} m')
        return distance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--map', required=True)
    parser.add_argument('--goals', required=True)
    parser.add_argument('--clearance', type=float, default=.4)
    parser.add_argument('--output', default='evidence/map_goals.png')
    args = parser.parse_args()
    saved = SavedMap(args.map)
    goals = load_goals(args.goals)
    image = cv2.cvtColor(saved.image, cv2.COLOR_GRAY2BGR)
    for goal in goals:
        distance = saved.check(goal['x'], goal['y'], args.clearance)
        print(f"{goal['name']}: x={goal['x']:.3f}, y={goal['y']:.3f}, yaw={goal['yaw']:.3f}, clearance={distance:.3f} m")
        row, col = saved.pixel(goal['x'], goal['y'])
        angle = goal['yaw']-saved.origin[2]
        cv2.circle(image, (col,row), 6, (0,0,255), -1)
        cv2.arrowedLine(image, (col,row), (col+int(20*math.cos(angle)), row-int(20*math.sin(angle))), (0,0,255),2)
        cv2.putText(image, goal['name'], (col+8,row-8),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,0,200),1,cv2.LINE_AA)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(args.output,image)
    print('Static clearance passed; live Nav2 path validation is still required.')
