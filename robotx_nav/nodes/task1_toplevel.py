#!/usr/bin/env python

""" task 1:
    -----------------
    Created by Ren Ye @ 2016-11-06
    Authors: Ren Ye, Reinaldo
    -----------------

    <put the descriptions from robotx.org pdf file>

    <put the algorithms in natural language, can use bullet points, best is to use markdown format>

    <if you have plan b, can put it here>

    ## example ##
    + Go to start point
    + Rotate in position to detect red_1 and green_1 buoys
    + Plot perpendicular waypoints wrt to position of red and green buoys
    + Move towards waypoints move_base_forward
    + meanwhile requesting positions of red_2 and green_2
    + 	shutdown move_base_forward, create new move_base_forward towards mid of red_2 and green_2

    <change log put here>
    ### @ 2016-11-06 ###
    + create template

    renye's approach:
    1. drive to gps waypoint
    2. slowly in place rotate # noneed
    3. detect red and green totems by any camera
    4. rotate to bow to red and green totems
    5. roi of red in bow/left and roi of green in bow/right, calculate center
    6. drive until roi vanishes from both bow cameras, detect totem from port and starboard
    7. see new roi from bow
    8. drive with 5 and 6

    reinaldo's approach:
    1. fill bucket of markers array until full
    2. do k-means clustering to differentiate monocolor totems
    3. get closest pairs 
    4. plan based on pairs, replan if new plan is far from old plan
    5. loop to 2. 
    6. terminate if displacement from start to end > termination_distance 


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
from move_base_force_cancel import ForceCancel
from tf.transformations import euler_from_quaternion
from nav_msgs.msg import Odometry

def constant_heading(goal):
    constant_obj = Forward(nodename="constant_heading", target=goal, waypoint_separation=5, is_relative=False)

def cancel_forward():
    os.system('rosnode kill constant_heading')

class PassGates(object):
    pool = mp.Pool(5)

    x0, y0, yaw0= 0, 0, 0
    MAX_DATA=30

    markers_array=MarkerArray()

    red_totem=np.zeros((MAX_DATA, 2)) #unordered list
    green_totem=np.zeros((MAX_DATA, 2))

    red_centers=np.zeros((2, 2)) #ordered list of centers x, y
    green_centers=np.zeros((2, 2))

    red_position=np.zeros((2, 2)) #ordered list of centers x, y
    green_position=np.zeros((2, 2))

    red_counter=0
    green_counter=0


    replan_min=5

    termination_displacement=60

    def __init__(self):
	print("starting task 1")
        rospy.init_node('task_1', anonymous=True)
        rospy.Subscriber("/fake_marker_array", MarkerArray, self.marker_callback, queue_size = 50)
        self.marker_pub= rospy.Publisher('waypoint_markers', Marker, queue_size=5)

        self.odom_received = False
        #rospy.wait_for_message("/odom", Odometry)
        #rospy.Subscriber("/odom", Odometry, self.odom_callback, queue_size=50)
        rospy.wait_for_message("/odometry/filtered/global", Odometry)
        rospy.Subscriber("/odometry/filtered/global", Odometry, self.odom_callback, queue_size=50)
        while not self.odom_received:
           rospy.sleep(1)
	print("odom received")

        init_position =np.array([self.x0, self.y0, 0])
        prev_target=np.array([self.x0, self.y0, 0])


        while(self.red_counter<self.MAX_DATA and self.green_counter<self.MAX_DATA):
            #wait for data bucket to fill up
            time.sleep(1)
	print("bucket full")

	    

        while not rospy.is_shutdown():
            self.matrix_reorder()
	    print("reorder complete")
            target = self.plan_waypoint()
            print(target)


            if self.euclid_distance(target, prev_target)>self.replan_min:
                #replan
                #force cancel
                self.pool.apply(cancel_forward)
                #plan new constant heading
	        print("replan")
                self.pool.apply_async(constant_heading, args = (target, ))
                prev_target=target
            else:
                pass
            #termination condition
            if self.euclid_distance(np.array([self.x0, self.y0, 0]), init_position)>self.termination_displacement:
		self.pool.apply(cancel_forward)
                print("Task 1 Completed")
                break

            time.sleep(1)

	self.pool.close()
	self.pool.join()


    def plan_waypoint(self):
        distance=20
        dis_red=1000
        dis_green=1000
            #find closest available totem pairs

        for m in self.red_position:
            if self.distance_from_boat(m) < dis_red:
                nearest_red=m
                dis_red=self.distance_from_boat(m)

        for n in self.green_position:
            if self.distance_from_boat(n) < dis_green:
                nearest_green=n
                dis_green=self.distance_from_boat(n)
        #plan
        dis=nearest_red-nearest_green
        [x_center, y_center]=[(nearest_red[0]+nearest_green[0])/2, (nearest_red[1]+nearest_green[1])/2]

        if math.sqrt(dis.dot(dis.T)) <20:
            theta=math.atan2(math.sin(math.atan2(nearest_green[1]-nearest_red[1], nearest_green[0]-nearest_red[0])+math.pi/2), math.cos(math.atan2(nearest_green[1]-nearest_red[1], nearest_green[0]-nearest_red[0])+math.pi/2))
            #theta = math.atan2(nearest_green[1]-nearest_red[1], nearest_green[0]-nearest_red[0])+math.pi/2
        else:
            theta = math.atan2(nearest_green[1]-nearest_red[1], nearest_green[0]-nearest_red[0])+math.atan2(10,30)

        return np.array([x_center+distance*math.cos(theta), y_center+distance*math.sin(theta), theta])


    def distance_from_boat(self, target):
        return math.sqrt((target[0]-self.x0)**2+(target[1]-self.y0)**2)

    def euclid_distance(self, target1, target2):
        return math.sqrt((target1[0]-target2[0])**2+(target1[1]-target2[1])**2)

    def is_complete(self):
        pass

    # def search_marker(self, obj_type, obj_color, markers_list):
    #     #pose_list is list that stores Pose obj for requested markers
    #     N=len(pose_list)

    #     if len(markers_list.markers)>0:
    #         for i in range(len(markers_list.markers)):
    #             if markers_list.markers[i].type == obj_type and markers_list.markers[i].id==obj_color:
    #                 #may append more than 1 markers

    #                 if obj_color==0:
    #                     self.red_totem[self.red_counter%self.MAX_DATA]=[markers_list.markers[i].pose.position.x, markers_list.markers[i].pose.position.y]
    #                     self.red_counter+=1
    #                 elif obj_color==1:
    #                     self.green_totem[self.green_counter%self.MAX_DATA]=[markers_list.markers[i].pose.position.x, markers_list.markers[i].pose.position.y]
    #                     self.green_counter+=1
    #             else:
    #                 pass

    #         # use mod, will not overflow
    #         # if len(pose_list)>self.MAX_DATA:
    #         #     pose_list.pop(0)
    #         return True
    #     else:
    #         return False

    def marker_callback(self, msg):
        # #updates markers_array
        # self.search_marker(3, 0 , self.red_totem, msg)
        # self.search_marker(3, 1 , self.green_totem, msg)
        # print self.red_totem
        if len(msg.markers)>0:
            for i in range(len(msg.markers)):
                if msg.markers[i].type == 3:
                    #may append more than 1 markers

                    if msg.markers[i].id == 0:
                        self.red_totem[self.red_counter%self.MAX_DATA]=[msg.markers[i].pose.position.x, msg.markers[i].pose.position.y]
                        self.red_counter+=1
                    elif msg.markers[i].id == 1:
                        self.green_totem[self.green_counter%self.MAX_DATA]=[msg.markers[i].pose.position.x, msg.markers[i].pose.position.y]
                        self.green_counter+=1
                else:
                    pass

        # list is full
        if (self.red_counter>self.MAX_DATA):
            red_kmeans = KMeans(n_clusters=2).fit(self.red_totem)
            self.red_centers=red_kmeans.cluster_centers_
        if(self.green_counter>self.MAX_DATA):
            green_kmeans = KMeans(n_clusters=2).fit(self.green_totem)
            self.green_centers=green_kmeans.cluster_centers_

        #visualize markers in rviz
        for i in range(len(msg.markers)):
            self.marker_pub.publish(msg.markers[i])

    def matrix_reorder(self):

        if self.red_centers[0].dot(self.red_centers[0].T)< self.red_centers[1].dot(self.red_centers[1].T):
            self.red_position=self.red_centers

        else:
            self.red_position[0]=self.red_centers[1]
            self.red_position[1]=self.red_centers[0]

        if self.green_centers[0].dot(self.green_centers[0].T)< self.green_centers[1].dot(self.green_centers[1].T):
            self.green_position=self.green_centers
        else:
            self.green_position[0]=self.green_centers[1]
            self.green_position[1]=self.green_centers[0]

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
        PassGates()
        # stage 1: gps
    except rospy.ROSInterruptException:
        rospy.loginfo("Task 1 Finished")
