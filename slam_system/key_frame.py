"""
Key frame class.

Created by Luke, 2018.9
"""

import scipy.io as sio


class KeyFrame:
    """This is a class for keyframe in mapping."""
    def __init__(self, img, img_index, center, rotation, u, v, pan, tilt, f):
        """
        :param img: image array for keyframe
        :param img_index: index in sequence
        :param center: camera center array [3]
        :param rotation: base rotation matrix array [3, 3]
        :param u: parameter u
        :param v: parameter v
        :param pan: camera pose, pan angle
        :param tilt: camera pose, tilt angle
        :param f: camera pose, focal length
        """
        self.img = img
        self.img_index = img_index

        """feature points"""

        # a list of key point object (the first return value of detect_compute_sift function)
        self.feature_pts = []

        # a [N, 128] int array (the second return value of detect_compute_sift function)
        self.feature_des = []

        # a [N] int array of index for keypoint in global_ray
        self.landmark_index = []

        """camera pose"""
        self.pan, self.tilt, self.f = pan, tilt, f

        """camera parameters"""
        # camera center [3] array
        self.center = center
        # rotation matrix [3, 3] array
        self.base_rotation = rotation
        self.u = u
        self.v = v

    def get_feature_num(self):
        """
        :return: keypoint number
        """
        return len(self.feature_pts)

    def save_to_mat(self, path):
        """
        :param path: save path for key frame
        """
        keyframe_data = dict()
        keyframe_data['img_index'] = self.img_index
        keyframe_data['feature_pts'] = self.feature_pts
        keyframe_data['feature_des'] = self.feature_des
        keyframe_data['landmark_index'] = self.landmark_index
        keyframe_data['camera_pose'] = self.pan, self.tilt, self.f
        keyframe_data['center'] = self.center
        keyframe_data['base_rotation'] = self.base_rotation
        keyframe_data['u'] = self.u
        keyframe_data['v'] = self.v
        sio.savemat(path, mdict=keyframe_data)

    def load_mat(self, path):
        """
        :param path: load path for .mat file
        """
        keyframe_data = sio.loadmat(path)
        self.img_index = keyframe_data['img_index'].squeeze(1)
        self.feature_pts = keyframe_data['feature_pts'].squeeze(1)
        self.feature_des = keyframe_data['feature_des'].squeeze(1)
        self.landmark_index = keyframe_data['landmark_index'].squeeze(1)
        self.pan, self.tilt, self.f = keyframe_data['camera_pose'].squeeze(1)
        self.center = keyframe_data['center'].squeeze(1)
        self.base_rotation = keyframe_data['base_rotation'].squeeze(1)
        self.u = keyframe_data['u'].squeeze(1)
        self.v = keyframe_data['v'].squeeze(1)
