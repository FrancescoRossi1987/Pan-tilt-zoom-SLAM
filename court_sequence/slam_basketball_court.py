"""
PTZ camera SLAM tested on synthesized data
2018.8
"""

import matplotlib.pyplot as plt
import numpy as np
import scipy.io as sio
import random
import cv2 as cv
import statistics
from sklearn.preprocessing import normalize
from math import *
from transformation import TransFunction
import scipy.signal as sig


class PtzSlam:
    def __init__(self, model_path, annotation_path, data_path):

        self.width = 1280
        self.height = 720
        self.img = np.zeros((self.height, self.width, 3), np.uint8)

        court_model = sio.loadmat(model_path)
        self.line_index = court_model['line_segment_index']
        self.points = court_model['points']

        seq = sio.loadmat(annotation_path)
        self.annotation = seq["annotation"]
        self.meta = seq['meta']

        data = sio.loadmat(data_path)

        # this is synthesized rays to generate 2d-point. Real data does not have this variable
        self.all_rays = np.column_stack((data["rays"], data["features"]))

        """
        initialize the fixed parameters of our algorithm
        u, v, base_rotation and c
        """

        self.u, self.v = self.annotation[0][0]['camera'][0][0:2]
        self.base_rotation = np.zeros([3, 3])
        cv.Rodrigues(self.meta[0][0]["base_rotation"][0], self.base_rotation)
        self.c = self.meta[0][0]["cc"][0]

        """
        parameters to be updated
        """
        self.camera_pose = np.ndarray([3])
        self.delta_pan, self.delta_tilt, self.delta_zoom = [0, 0, 0]

        self.ray_global = np.ndarray([0, 2])
        self.des_global = np.ndarray([0, 32])
        self.p_global = np.zeros([3, 3])

        self.ground_truth_pan = np.ndarray([self.annotation.size])
        self.ground_truth_tilt = np.ndarray([self.annotation.size])
        self.ground_truth_f = np.ndarray([self.annotation.size])
        for i in range(self.annotation.size):
            self.ground_truth_pan[i], self.ground_truth_tilt[i], self.ground_truth_f[i] \
                = self.annotation[0][i]['ptz'].squeeze()

        self.ground_truth_pan = sig.savgol_filter(self.ground_truth_pan, 25, 2)
        self.ground_truth_tilt = sig.savgol_filter(self.ground_truth_tilt, 25, 2)
        self.ground_truth_f = sig.savgol_filter(self.ground_truth_f, 25, 2)


    def get_ptz(self, index):
        return np.array([self.ground_truth_pan[index], self.ground_truth_tilt[index], self.ground_truth_f[index]])

    def test_harris(self):
        img1 = cv.imread("./basketball/basketball/synthesize_images/2.jpg")

        img1_gray = cv.cvtColor(img1, cv.COLOR_BGR2GRAY)

        img2 = cv.imread("./basketball/basketball/synthesize_images/200.jpg")

        img2_gray = cv.cvtColor(img2, cv.COLOR_BGR2GRAY)

        # print(img1.shape)

        # mask = np.zeros(img1.shape, np.uint8)
        #
        # mask[180:540, 320:960] = 1
        # print("fuuuuuuuuuuuck", type(mask))
        corners = cv.goodFeaturesToTrack(img1_gray, 30, 0.01, 10)

        print(corners.shape)


        # corners2 = np.ndarray(corners.shape)

        # for i in range(len(corners)):
        #     cv.circle(img1, (int(corners[i,0,0]), int(corners[i,0,1])), color=(255, 0, 0), radius=8, thickness=2 )


        # print("corners", corners.shape)
        corners2, st, err = cv.calcOpticalFlowPyrLK(img1_gray, img2_gray, corners, None, winSize=(31,31))

        print(corners.shape, corners2.shape)

        print(st)

        # print(corners - corners2)

        for i in range(len(corners)):
            if st[i][0] == 1 and err[i] < 5:
                x1, y1 = round(corners[i,0,0]),  round(corners[i,0,1])
                x2, y2 = round(corners2[i,0,0]),  round(corners2[i,0,1])
                cv.circle(img1, (x1, y1), color=(0, 255, 0), radius=8,
                          thickness=1)
                cv.circle(img2, (x2, y2), color=(0, 255, 0), radius=8,
                          thickness=1)

                print(i, x1-x2, y1-y2)
            # cv.circle(img1, (int(corners[i,0,0]), int(corners[i,0,1])), color=(255, 0, 0), radius=8, thickness= 2 )
            # print((int(corners[i, 0, 0]), int(corners[i, 0, 1])) - (int(corners2[i, 0, 0]), int(corners2[i, 0, 1])))

        cv.imshow("fuck", img1)
        cv.imwrite("./test1.jpg", img1)
        print("err\n", err.shape)

        # print("status", st)



        # for i in range(len(corners2)):
        #     if st[i][0] == 1:
        #         cv.circle(img2, (int(corners2[i,0,0]), int(corners2[i,0,1])), color=(255, 0, 0), radius=8, thickness=2 )
        cv.imshow("fuck2", img2)
        cv.imwrite("./test2.jpg", img2)


    # return [CornerNumber * 1 * 2]
    def get_basketball_image(self, index):

        img = cv.imread("./basketball/basketball/synthesize_images/" + str(index) + ".jpg")

        img_gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

        # corners = cv.goodFeaturesToTrack(img_gray, 30, 0.01, 10)
        return img_gray



    # compute the H_jacobi matrix
    # rays [RayNumber * 2]
    # return [2 * RayNumber, 3 + 2 * RayNumber]
    def compute_new_jacobi(self, camera_pan, camera_tilt, foc, rays):
        ray_num = len(rays)

        delta_angle = 0.001
        delta_f = 0.1

        jacobi_h = np.ndarray([2 * ray_num, 3 + 2 * ray_num])

        for i in range(ray_num):
            x_delta_pan1, y_delta_pan1 = TransFunction.from_pan_tilt_to_2d(
                self.u, self.v, foc, camera_pan - delta_angle, camera_tilt, rays[i][0], rays[i][1])

            x_delta_pan2, y_delta_pan2 = TransFunction.from_pan_tilt_to_2d(
                self.u, self.v, foc, camera_pan + delta_angle, camera_tilt, rays[i][0], rays[i][1])

            x_delta_tilt1, y_delta_tilt1 = TransFunction.from_pan_tilt_to_2d(
                self.u, self.v, foc, camera_pan, camera_tilt - delta_angle, rays[i][0], rays[i][1])

            x_delta_tilt2, y_delta_tilt2 = TransFunction.from_pan_tilt_to_2d(
                self.u, self.v, foc, camera_pan, camera_tilt + delta_angle, rays[i][0], rays[i][1])

            x_delta_f1, y_delta_f1 = TransFunction.from_pan_tilt_to_2d(
                self.u, self.v, foc - delta_f, camera_pan, camera_tilt, rays[i][0], rays[i][1])

            x_delta_f2, y_delta_f2 = TransFunction.from_pan_tilt_to_2d(
                self.u, self.v, foc + delta_f, camera_pan, camera_tilt, rays[i][0], rays[i][1])

            x_delta_theta1, y_delta_theta1 = TransFunction.from_pan_tilt_to_2d(
                self.u, self.v, foc, camera_pan, camera_tilt, rays[i][0] - delta_angle, rays[i][1])

            x_delta_theta2, y_delta_theta2 = TransFunction.from_pan_tilt_to_2d(
                self.u, self.v, foc, camera_pan, camera_tilt, rays[i][0] + delta_angle, rays[i][1])

            x_delta_phi1, y_delta_phi1 = TransFunction.from_pan_tilt_to_2d(
                self.u, self.v, foc, camera_pan, camera_tilt, rays[i][0], rays[i][1] - delta_angle)
            x_delta_phi2, y_delta_phi2 = TransFunction.from_pan_tilt_to_2d(
                self.u, self.v, foc, camera_pan, camera_tilt, rays[i][0], rays[i][1] + delta_angle)

            jacobi_h[2 * i][0] = (x_delta_pan2 - x_delta_pan1) / (2 * delta_angle)
            jacobi_h[2 * i][1] = (x_delta_tilt2 - x_delta_tilt1) / (2 * delta_angle)
            jacobi_h[2 * i][2] = (x_delta_f2 - x_delta_f1) / (2 * delta_f)

            jacobi_h[2 * i + 1][0] = (y_delta_pan2 - y_delta_pan1) / (2 * delta_angle)
            jacobi_h[2 * i + 1][1] = (y_delta_tilt2 - y_delta_tilt1) / (2 * delta_angle)
            jacobi_h[2 * i + 1][2] = (y_delta_f2 - y_delta_f1) / (2 * delta_f)

            for j in range(ray_num):
                if j == i:
                    jacobi_h[2 * i][3 + 2 * j] = (x_delta_theta2 - x_delta_theta1) / (2 * delta_angle)
                    jacobi_h[2 * i][3 + 2 * j + 1] = (x_delta_phi2 - x_delta_phi1) / (2 * delta_angle)

                    jacobi_h[2 * i + 1][3 + 2 * j] = (y_delta_theta2 - y_delta_theta1) / (2 * delta_angle)
                    jacobi_h[2 * i + 1][3 + 2 * j + 1] = (y_delta_phi2 - y_delta_phi1) / (2 * delta_angle)
                else:
                    jacobi_h[2 * i][3 + 2 * j] = jacobi_h[2 * i][3 + 2 * j + 1] = \
                        jacobi_h[2 * i + 1][3 + 2 * j] = jacobi_h[2 * i + 1][3 + 2 * j + 1] = 0

        return jacobi_h

    # return all 2d points(with features), corresponding rays(with features) and indexes of these points IN THE IMAGE.
    def get_observation_from_rays(self, pan, tilt, f, rays):
        points = np.ndarray([0, 2])
        inner_rays = np.ndarray([0, 2])
        index = np.ndarray([0])

        for j in range(len(rays)):
            tmp = TransFunction.from_pan_tilt_to_2d(self.u, self.v, f, pan, tilt, rays[j][0], rays[j][1])
            if 0 < tmp[0] < self.width and 0 < tmp[1] < self.height:
                inner_rays = np.row_stack([inner_rays, rays[j]])
                points = np.row_stack([points, np.asarray(tmp)])
                index = np.concatenate([index, [j]], axis=0)

        return points, inner_rays, index

    # get a list of rays(with features) from 2d points and camera pose
    # points [PointNumber * 2]
    def get_rays_from_observation(self, pan, tilt, f, points):
        rays = np.ndarray([0, 2])
        for i in range(len(points)):
            angles = TransFunction.from_2d_to_pan_tilt(self.u, self.v, f, pan, tilt, points[i][0], points[i][1])
            rays = np.row_stack([rays, angles])
        return rays

    # draw some colored points in img
    def visualize_points(self, points, pt_color):
        for j in range(len(points)):
            cv.circle(self.img, (int(points[j][0]), int(points[j][1])), color=pt_color, radius=8, thickness=2)

    # output the error of camera pose compared to ground truth
    def output_camera_error(self, now_index):
        ground_truth = self.get_ptz(now_index)
        pan, tilt, f = self.camera_pose - ground_truth
        print("%.3f %.3f, %.1f" % (pan, tilt, f), "\n")

    # output the error of global rays compared to ground truth
    def output_ray_error(self):
        theta_list = []
        phi_list = []
        for j in range(len(self.ray_global)):
            for k in range(len(self.all_rays)):
                if np.linalg.norm(self.ray_global[j][2:18] - self.all_rays[k][2:18]) < 0.01:
                    tmp = self.ray_global[j][0:2] - self.all_rays[k][0:2]
                    theta_list.append(tmp[0])
                    phi_list.append(tmp[1])
                    break
        print("theta-mean-error %.4f" % np.mean(theta_list), "sdev %.4f" % statistics.stdev(theta_list))
        print("phi---mean-error %.4f" % np.mean(phi_list), "sdev %.4f" % statistics.stdev(phi_list), "\n")

    def main_algorithm(self):

        # first ground truth camera pose
        self.camera_pose = self.get_ptz(0)

        # first frame to initialize global_rays
        first_frame = self.get_basketball_image(0)
        first_frame_kp = cv.goodFeaturesToTrack(first_frame, 30, 0.01, 10)

        # use key points in first frame to get init rays
        init_rays = self.get_rays_from_observation(
            self.camera_pose[0], self.camera_pose[1], self.camera_pose[2], first_frame_kp.squeeze())

        # add rays in frame 1 to global rays
        self.ray_global = np.concatenate([self.ray_global, init_rays], axis=0)


        # initialize global p using global rays
        self.p_global = 0.001 * np.eye(3 + 2 * len(self.ray_global))
        self.p_global[2][2] = 1

        # q_k: covariance matrix of noise for state(camera pose)
        q_k = 5 * np.diag([0.001, 0.001, 1])

        previous_frame_kp = first_frame_kp
        previous_index = np.array([i for i in range(len(self.ray_global))])

        for i in range(1, self.annotation.size):

            print("=====The ", i, " iteration=====%d\n" % len(self.ray_global))

            self.img.fill(255)

            # ground truth features for next frame. In real data we do not need to compute that
            # next_frame_kp = self.get_basketball_image_features(i)
            next_frame_kp, status, err = cv.calcOpticalFlowPyrLK(
                self.get_basketball_image(i-1), self.get_basketball_image(i), previous_frame_kp, None, winSize=(31, 31))


            matched_kp = np.ndarray([0,  2])
            next_index = np.ndarray([0])
            for j in range(len(next_frame_kp)):
                if err[j] < 3:
                    next_index = np.concatenate([next_index, [previous_index[j]]], axis=0)
                    matched_kp = np.row_stack([matched_kp, next_frame_kp[j][0]])

            print("helooooooooooooo")

            # add the camera pose with constant speed model
            self.camera_pose += [self.delta_pan, self.delta_tilt, self.delta_zoom]

            # get 2d points, rays and indexes in all landmarks with predicted camera pose
            predict_points, predict_rays, inner_point_index = self.get_observation_from_rays(
                self.camera_pose[0], self.camera_pose[1], self.camera_pose[2], self.ray_global)

            # update p_global
            self.p_global[0:3, 0:3] = self.p_global[0:3, 0:3] + q_k


            # compute y_k
            y_k = np.ndarray([0])


            matched_inner_point_index = np.ndarray([0])
            ptr = 0
            for j in range(len(matched_kp)):

                while inner_point_index[ptr] < next_index[j]:
                    ptr += 1
                if inner_point_index[ptr] > next_index[j]:
                    continue
                y_k = np.concatenate([y_k, matched_kp[j] - predict_points[ptr]], axis=0)
                matched_inner_point_index = np.concatenate([matched_inner_point_index, [next_index[j]]], axis=0)


            # get predicted_x: combine 3 camera parameters and rays
            predict_x = self.camera_pose
            for j in range(len(matched_inner_point_index)):
                predict_x = np.concatenate([predict_x, self.ray_global[int(matched_inner_point_index[j])][0:2]], axis=0)

            # get p matrix for this iteration from p_global
            p_index = (np.concatenate([[0, 1, 2], matched_inner_point_index + 3, matched_inner_point_index + len(matched_inner_point_index) + 3])).astype(int)
            p = self.p_global[p_index][:, p_index]

            # compute jacobi
            jacobi = self.compute_new_jacobi(camera_pan=self.camera_pose[0], camera_tilt=self.camera_pose[1],
                                             foc=self.camera_pose[2], rays=self.ray_global[matched_inner_point_index.astype(int)])

            # get Kalman gain
            r_k = 2 * np.eye(2 * len(matched_inner_point_index))
            s_k = np.dot(np.dot(jacobi, p), jacobi.T) + r_k

            k_k = np.dot(np.dot(p, jacobi.T), np.linalg.inv(s_k))

            k_mul_y = np.dot(k_k, y_k)

            # output result for updating camera: before
            print("before update camera:\n")
            self.output_camera_error(i)

            # update camera pose
            self.camera_pose += k_mul_y[0:3]

            # output result for updating camera: after
            print("after update camera:\n")
            self.output_camera_error(i)

            # update speed model
            self.delta_pan, self.delta_tilt, self.delta_zoom = k_mul_y[0:3]



            # initialize new landmarks
            # for j in range(len(next_frame_kp)):
            #     has_point = False
            #     for k in range(len(self.ray_global)):
            #         if np.linalg.norm(next_frame[j][2:18] - self.ray_global[k][2:18]) < 0.01:
            #             has_point = True
            #             break
            #
            #     # if no corresponding points in global_rays, we should add it to global ray.
            #     if not has_point:
            #         new_ray = self.get_rays_from_observation(
            #             self.camera_pose[0], self.camera_pose[1], self.camera_pose[2], next_frame[j:j + 1, :])
            #         self.ray_global = np.concatenate([self.ray_global, new_ray], axis=0)
            #         self.p_global = np.row_stack((self.p_global, np.zeros([2, self.p_global.shape[1]])))
            #         self.p_global = np.column_stack((self.p_global, np.zeros([self.p_global.shape[0], 2])))
            #         self.p_global[self.p_global.shape[0] - 1, self.p_global.shape[1] - 1] = 0.01



            # update global rays
            for j in range(len(matched_inner_point_index)):
                self.ray_global[int(matched_inner_point_index[j])][0:2] += k_mul_y[2 * j + 3: 2 * j + 5]



            # update global p
            update_p = np.dot(np.eye(3 + 2 * len(matched_inner_point_index)) - np.dot(k_k, jacobi), p)
            self.p_global[0:3, 0:3] = update_p[0:3, 0:3]
            for j in range(len(matched_inner_point_index)):
                for k in range(len(matched_inner_point_index)):
                    self.p_global[3+2 * int(matched_inner_point_index[j]), 3 + 2 * int(matched_inner_point_index[k])] = \
                        update_p[3+2*j, 3+2*k]
                    self.p_global[3 + 2 * int(matched_inner_point_index[j]) + 1,  3 + 2 * int(matched_inner_point_index[k]) + 1] = \
                        update_p[3 + 2 * j + 1, 3 + 2 * k + 1]

            points_update, in_rays_update, index_update = self.get_observation_from_rays(
                self.camera_pose[0], self.camera_pose[1], self.camera_pose[2],  self.ray_global)

            self.visualize_points(predict_points, (255, 0, 0))
            self.visualize_points(matched_kp, (0, 0, 0))
            # for j in range(len(next_frame_kpt_frame_kp[j].pt[0]), int(next_frame_kp[j].pt[1])), color=(0,0,0), radius=8, thickness=2)
            self.visualize_points(points_update, (0, 0, 255))

            cv.imshow("test", self.img)
            cv.waitKey(0)


if __name__ == "__main__":

    slam = PtzSlam("./basketball/basketball_model.mat",
                   "./basketball/basketball/basketball_anno.mat",
                   "./synthesize_data.mat")

    slam.test_harris()
    # slam.test_orb()
    # slam.get_seq3_image(3)

    slam.main_algorithm()