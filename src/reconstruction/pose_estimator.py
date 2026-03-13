"""
Pose Estimator - Camera pose estimation from image sequences

Uses feature matching and structure-from-motion for camera pose recovery.
Provides incremental pose estimation for sequential frames.
"""

import numpy as np
import cv2
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CameraPose:
    """Camera pose representation"""
    R: np.ndarray  # 3x3 rotation matrix
    t: np.ndarray  # 3x1 translation vector
    frame_id: int
    inliers: int = 0
    
    @property
    def T(self) -> np.ndarray:
        """4x4 transformation matrix"""
        T = np.eye(4)
        T[:3, :3] = self.R
        T[:3, 3] = self.t.flatten()
        return T


class PoseEstimator:
    """Estimates camera poses from image sequences"""
    
    def __init__(self, config: dict):
        """
        Initialize pose estimator
        
        Args:
            config: Configuration dict with keys:
                - focal_length: Camera focal length in pixels (default: auto-estimate)
                - principal_point: [cx, cy] principal point (default: image center)
                - feature_detector: 'sift' or 'orb' (default: 'sift')
                - min_features: Minimum features for pose estimation (default: 100)
                - ransac_threshold: RANSAC inlier threshold in pixels (default: 1.0)
        """
        self.focal_length = config.get('focal_length', None)
        self.principal_point = config.get('principal_point', None)
        self.feature_detector_type = config.get('feature_detector', 'sift')
        self.min_features = config.get('min_features', 100)
        self.ransac_threshold = config.get('ransac_threshold', 1.0)
        
        # Initialize feature detector
        if self.feature_detector_type == 'sift':
            self.feature_detector = cv2.SIFT_create(nfeatures=2000)
            self.matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
        else:  # ORB
            self.feature_detector = cv2.ORB_create(nfeatures=2000)
            self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            
        self.poses: List[CameraPose] = []
        self.K: Optional[np.ndarray] = None  # Camera intrinsic matrix
        
    def _get_camera_matrix(self, image_shape: Tuple[int, int]) -> np.ndarray:
        """
        Get or estimate camera intrinsic matrix
        
        Args:
            image_shape: (height, width) of image
            
        Returns:
            3x3 camera intrinsic matrix
        """
        h, w = image_shape
        
        if self.K is not None:
            return self.K
            
        # Estimate from image size if not provided
        if self.focal_length is None:
            # Typical assumption: focal length ~ image width
            focal = max(w, h)
        else:
            focal = self.focal_length
            
        if self.principal_point is None:
            cx, cy = w / 2.0, h / 2.0
        else:
            cx, cy = self.principal_point
            
        self.K = np.array([
            [focal, 0, cx],
            [0, focal, cy],
            [0, 0, 1]
        ], dtype=np.float32)
        
        return self.K
        
    def _detect_and_match(self, img1: np.ndarray, img2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect features and match between two images
        
        Args:
            img1: First image (grayscale)
            img2: Second image (grayscale)
            
        Returns:
            Tuple of (pts1, pts2) matched point arrays
        """
        # Detect and compute
        kp1, desc1 = self.feature_detector.detectAndCompute(img1, None)
        kp2, desc2 = self.feature_detector.detectAndCompute(img2, None)
        
        if desc1 is None or desc2 is None or len(kp1) < 10 or len(kp2) < 10:
            return np.array([]), np.array([])
            
        # Match features
        matches = self.matcher.knnMatch(desc1, desc2, k=2)
        
        # Apply Lowe's ratio test
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < 0.75 * n.distance:
                    good_matches.append(m)
                    
        if len(good_matches) < self.min_features:
            logger.warning(f"Only {len(good_matches)} matches found (min: {self.min_features})")
            
        # Extract matched points
        pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 2)
        pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 2)
        
        return pts1, pts2
        
    def estimate_pose_pair(self, img1: np.ndarray, img2: np.ndarray, frame_id: int) -> Optional[CameraPose]:
        """
        Estimate relative pose between two images
        
        Args:
            img1: First image (reference)
            img2: Second image (current)
            frame_id: Frame ID for pose
            
        Returns:
            CameraPose or None if estimation failed
        """
        # Convert to grayscale if needed
        if len(img1.shape) == 3:
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        else:
            gray1 = img1
            
        if len(img2.shape) == 3:
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        else:
            gray2 = img2
            
        # Get camera matrix
        K = self._get_camera_matrix(gray1.shape)
        
        # Detect and match features
        pts1, pts2 = self._detect_and_match(gray1, gray2)
        
        if len(pts1) < self.min_features:
            logger.error(f"Not enough features for pose estimation: {len(pts1)}")
            return None
            
        # Estimate essential matrix
        E, mask = cv2.findEssentialMat(
            pts1, pts2, K,
            method=cv2.RANSAC,
            prob=0.999,
            threshold=self.ransac_threshold
        )
        
        if E is None:
            logger.error("Essential matrix estimation failed")
            return None
            
        # Recover pose from essential matrix
        inliers, R, t, mask_pose = cv2.recoverPose(E, pts1, pts2, K, mask=mask)
        
        pose = CameraPose(
            R=R,
            t=t,
            frame_id=frame_id,
            inliers=inliers
        )
        
        logger.info(f"Pose estimated: {inliers} inliers, translation norm: {np.linalg.norm(t):.3f}")
        
        return pose
        
    def estimate_poses_sequential(self, images: List[np.ndarray]) -> List[CameraPose]:
        """
        Estimate poses for sequence of images (incremental SfM)
        
        Args:
            images: List of images in sequence
            
        Returns:
            List of camera poses (first pose is identity)
        """
        if len(images) < 2:
            logger.error("Need at least 2 images for pose estimation")
            return []
            
        poses = []
        
        # First pose is identity (world frame)
        poses.append(CameraPose(
            R=np.eye(3),
            t=np.zeros((3, 1)),
            frame_id=0,
            inliers=0
        ))
        
        # Accumulate transformations
        T_world = np.eye(4)
        
        for i in range(1, len(images)):
            # Estimate relative pose
            rel_pose = self.estimate_pose_pair(images[i-1], images[i], frame_id=i)
            
            if rel_pose is None:
                logger.warning(f"Failed to estimate pose for frame {i}, using previous pose")
                # Use previous pose (no motion assumption)
                poses.append(poses[-1])
                continue
                
            # Accumulate transformation
            T_rel = rel_pose.T
            T_world = T_world @ T_rel
            
            # Extract R and t from accumulated transformation
            R_world = T_world[:3, :3]
            t_world = T_world[:3, 3].reshape(3, 1)
            
            poses.append(CameraPose(
                R=R_world,
                t=t_world,
                frame_id=i,
                inliers=rel_pose.inliers
            ))
            
        self.poses = poses
        return poses
        
    def triangulate_points(self, 
                          img1: np.ndarray, 
                          img2: np.ndarray,
                          pose1: CameraPose,
                          pose2: CameraPose) -> Tuple[np.ndarray, np.ndarray]:
        """
        Triangulate 3D points from two views
        
        Args:
            img1: First image
            img2: Second image
            pose1: Camera pose for first image
            pose2: Camera pose for second image
            
        Returns:
            Tuple of (points_3d, colors) as Nx3 arrays
        """
        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2
        
        # Match features
        pts1, pts2 = self._detect_and_match(gray1, gray2)
        
        if len(pts1) < 10:
            return np.array([]), np.array([])
            
        # Projection matrices
        K = self._get_camera_matrix(gray1.shape)
        P1 = K @ np.hstack([pose1.R, pose1.t])
        P2 = K @ np.hstack([pose2.R, pose2.t])
        
        # Triangulate
        points_4d = cv2.triangulatePoints(P1, P2, pts1.T, pts2.T)
        points_3d = (points_4d[:3, :] / points_4d[3, :]).T
        
        # Get colors from first image
        colors = np.zeros((len(pts1), 3))
        for i, pt in enumerate(pts1):
            x, y = int(pt[0]), int(pt[1])
            if 0 <= y < img1.shape[0] and 0 <= x < img1.shape[1]:
                if len(img1.shape) == 3:
                    colors[i] = img1[y, x, :3] / 255.0  # BGR to RGB normalized
                else:
                    colors[i] = np.array([gray1[y, x]] * 3) / 255.0
                    
        return points_3d, colors
        
    def get_point_cloud(self, images: List[np.ndarray], poses: List[CameraPose]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate point cloud from images and poses
        
        Args:
            images: List of images
            poses: List of camera poses
            
        Returns:
            Tuple of (points_3d, colors) as Nx3 arrays
        """
        all_points = []
        all_colors = []
        
        # Triangulate between consecutive pairs
        for i in range(len(images) - 1):
            points, colors = self.triangulate_points(
                images[i], images[i+1],
                poses[i], poses[i+1]
            )
            
            if len(points) > 0:
                # Filter out points that are too far (likely outliers)
                distances = np.linalg.norm(points, axis=1)
                valid = distances < np.percentile(distances, 95)
                
                all_points.append(points[valid])
                all_colors.append(colors[valid])
                
        if len(all_points) == 0:
            return np.array([]), np.array([])
            
        points_3d = np.vstack(all_points)
        colors = np.vstack(all_colors)
        
        logger.info(f"Generated point cloud with {len(points_3d)} points")
        
        return points_3d, colors
