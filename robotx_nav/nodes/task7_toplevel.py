#!/usr/bin/env python

""" Mission 7-Detect and Deliver

    
    1. Random walk with gaussian at center of map until station position is acquired
    2. loiter around until correct face seen

task 7:
    -----------------
    Created by Reinaldo@ 2016-12-07
    Authors: Reinaldo
    -----------------


"""
import rospy
import multiprocessing as mp
import math
import time
import numpy as np
import os
from sklearn.cluster import KMeans
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Point, Pose
from visualization_msgs.msg import MarkerArray, Marker
from move_base_forward import Forward
from move_base_waypoint import MoveTo
from move_base_loiter import Loiter
from move_base_aiming import Aiming

is_loitering=False

def loiter_work(target):
    print("loitering")
    is_loitering=True
    loiter_obj = Loiter(nodename="loiter", target=target, radius=5, polygon=6, is_ccw=True, is_relative=False)
    is_loitering=False

def aim_work(target, radius=2, duration=0, box=[5,0,0])):
    print("aiming")
    stationkeep_obj = StationKeeping(nodename="aiming", radius=radius, duration=duration, angle_tolerance=1*pi/180.0, box=box))


def moveto_work(target, is_newnode):
    print("moveto")
    moveto_obj = MoveTo(nodename="moveto", is_newnode=is_newnode, target=target, is_relative=False)


def cancel_loiter():
    os.system('rosnode kill loiter')

def cancel_aiming():
    os.system('rosnode kill aiming')

def cancel_moveto():
    os.system('rosnode kill moveto')



class DetectDeliver(object):
    pool = mp.Pool(5)
    map_dim = [[0, 40], [0, 40]]

    MAX_DATA=30
    x0, y0, yaw0= 0, 0, 0
    symbols=np.zeros((MAX_DATA, 2)) #unordered list
    symbols_counter=0

    def __init__(self, symbol_list):
        print("starting task 7")
        rospy.init_node('task_7', anonymous=True)
        rospy.Subscriber("/fake_symbols", MarkerArray, self.symbol_callback, queue_size = 50)
        self.marker_pub= rospy.Publisher('waypoint_markers', Marker, queue_size=5)

        self.odom_received = False
        rospy.wait_for_message("/odometry/filtered/global", Odometry)
        rospy.Subscriber("/odometry/filtered/global", Odometry, self.odom_callback, queue_size=50)
        while not self.odom_received:
           rospy.sleep(1)
        print("odom received")

        self.symbol_visited=0
	self.symbol_seen=0
	self.symbol_position=[0, 0, 0]
	self.station_seen=False #station here is cluster center of any face
	self.station_position=[0, 0]

	while not rospy.is_shutdown() and not self.station_seen:
	    #random walk around center
	    self.pool.apply(moveto_work, args=(self.random_walk(), True)) #blocked is fine
	
	#loiter around station until symbol's face seen
	loiter_radius=math.sqrt((self.x0-self.station_position[0])**2+(self.y0-self.station_position[1])**2)
	
        while not rospy.is_shutdown() and not self.symbol_seen:
	    self.loitering=is_loitering
	    if not self.loitering:
	    	self.pool.apply_async(loiter, args=())
		self.loitering=True
	        
		if loiter_radius>3:
		    loiter_radius-=1
		
	self.pool.apply(cancel_loiter)
	
	#moveto an offset, replan in the way
		

	#aiming to the box

        self.pool.close()
        self.pool.join()

    def is_complete(self):
        pass

    def random_walk(self):
        """ create random walk points and more favor towards center """
        x = random.gauss(np.mean(self.map_dim[0]), 0.25 * np.ptp(self.map_dim[0]))
        y = random.gauss(np.mean(self.map_dim[1]), 0.25 * np.ptp(self.map_dim[1]))

        return self.map_constrain(x, y)

    def map_constrain(self, x, y):
        """ constrain x and y within map """
        if x > np.max(self.map_dim[0]):
            x = np.max(self.map_dim[0])
        elif x < np.min(self.map_dim[0]):
            x = np.min(self.map_dim[0])
        else:
            x = x
        if y > np.max(self.map_dim[1]):
            y = np.max(self.map_dim[1])
        elif y < np.min(self.map_dim[1]):
            y = np.min(self.map_dim[1])
        else:
            y = y

        return [x, y, 0]

    def symbol_callback(self, msg):
        if len(msg.markers)>0:
	    if self.symbols_counter>self.MAX_DATA:
		       
              	station_kmeans = KMeans(n_clusters=1).fit(self.symbols)
            	self.station_center=station_kmeans.cluster_centers_

		self.station_position[0]=self.station_center[0][0]
		self.station_position[1]=self.station_center[0][1]
		self.station_seen=True	

            for i in range(len(msg.markers)):

		self.symbols[self.symbol_counter%self.MAX_DATA]=[msg.markers[i].pose.position.x, msg.markers[i].pose.position.y]
		self.symbols_counter+=1

            	
            	if msg.markers[i].type==self.symbol_list[0] and msg.markers[i].id==self.symbol_list[1]:
             	    #set position_list (not sure)
		    self.symbol_position[0]=msg.markers[i].pose.position.x
		    self.symbol_position[1]=msg.markers[i].pose.position.y
		    x = msg.markers[i].pose.orientation.x
        	    y = msg.markers[i].pose.orientation.y
        	    z = msg.markers[i].pose.orientation.z
        	    w = msg.markers[i].pose.orientation.w
        	    _, _, self.symbol_position[2] = euler_from_quaternion((x, y, z, w))
            	    if self.station_seen:
			self.symbol_seen=True


    def odom_callback(self, msg):
        """ call back to subscribe, get odometry data:
        pose and orientation of the current boat,
        suffix 0 is for origin """
        self.x0 = msg.pose.pose.position.x
        self.y0 = msg.pose.pose.position.y
        x = msg.pose.pose.orientation.x
        y = msg.pose.pose.orientation.y
        z = msg.pose.pose.orientation.z
        w = msg.pose.pose.orientation.w
        _, _, self.yaw0 = euler_from_quaternion((x, y, z, w))
        self.odom_received = True



if __name__ == '__main__':
    try:
	#[id,type]circle red
        DetectDeliver([0,1])

        # stage 1: gps
    except rospy.ROSInterruptException:
        rospy.loginfo("Task 7 Finished")
