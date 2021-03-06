from __future__ import division

import os
import sys
from shutil import copyfile

# tf
import numpy as np
import tensorflow as tf

# save result
import cv2
import PIL.Image as pil
import matplotlib.pyplot as plt
import trimesh

# path
_curr_path = os.path.abspath(__file__) # /home/..../face
_cur_dir = os.path.dirname(_curr_path) # ./
_tf_dir = os.path.dirname(_cur_dir) # ./
_deep_learning_dir = os.path.dirname(_tf_dir) # ../
print(_deep_learning_dir)
sys.path.append(_deep_learning_dir) # /home/..../pytorch3d

# save result
from src_common.common.face_io import write_self_camera, write_self_lm, write_NoW_lm

# graph
from src_tfGraph.build_graph import MGC_TRAIN

flags = tf.app.flags
#
flags.DEFINE_string("dataset_dir", "/home/jshang/SHANG_Data_MOUNT/141/GAFR_semi_10_28/54_All_MUL_MERGE", "Dataset directory")
flags.DEFINE_string("output_dir", "/home/jshang/SHANG_Data/1_eccv2020_testData/32_AFLW2000_MGCDepth", "Output directory")
flags.DEFINE_string("ckpt_file", "/home/jshang/SHANG_Data_MOUNT/139/DeepLearning/100_02_warpdepth_reg/model-350000", "checkpoint file")
flags.DEFINE_string("mode", 'test', "3DMM coeffient rank")
flags.DEFINE_string("format_global_list", '.jpg', "3DMM coeffient rank")

#
flags.DEFINE_integer("batch_size", 1, "The size of of a sample batch")
flags.DEFINE_integer("img_height", 224, "Image height")
flags.DEFINE_integer("img_width", 224, "Image width")

#
flags.DEFINE_string("net", 'resnet', "| facenet | resnet |")
flags.DEFINE_integer("num_source", 2, "source images (seq_length-1)")

# gpmm
flags.DEFINE_string("path_gpmm", "/home/jshang/SHANG_Data/ThirdLib/BFM2009/bfm09_dy_gyd_presplit.h5", "Dataset directory")
flags.DEFINE_integer("light_rank", 27, "3DMM coeffient rank")
flags.DEFINE_integer("gpmm_rank", 80, "3DMM coeffient rank")
flags.DEFINE_integer("gpmm_exp_rank", 64, "3DMM coeffient rank")

#
flags.DEFINE_boolean("flag_eval", True, "3DMM coeffient rank")
flags.DEFINE_boolean("flag_visual", False, "")
flags.DEFINE_boolean("flag_fore", False, "")

# eval
flags.DEFINE_boolean("flag_now", False, "3DMM coeffient rank")
flags.DEFINE_boolean("flag_mesh_id", False, "3DMM coeffient rank")
flags.DEFINE_boolean("flag_full", True, "3DMM coeffient rank")
# visual

flags.DEFINE_boolean("flag_overlay_save", False, "")
flags.DEFINE_boolean("flag_overlayOrigin_save", False, "")
flags.DEFINE_boolean("flag_main_save", False, "")
flags.DEFINE_boolean("flag_fml_5", False, "")

FLAGS = flags.FLAGS

"""
python ./test_unsupervise.py --mode test_one \
--dataset_dir /data/0_eccv2020_final/0_Benchmark_Server/32_AFLW2000_3D_tensor \
--output_dir /home/jshang/SHANG_Exp/ECCV2020/release_2020.07.10/0_local \
--ckpt_file /home/jshang/SHANG_Exp/ECCV2020/rebuttal_2020.04.04/final_model_main/70_21_warpdepth_reg/model-400000 \
--path_gpmm /home/jshang/SHANG_Data/ThirdLib/BFM2009/bfm09_trim_exp_uv_presplit.h5 \
--flag_fore 1 \
--flag_mesh_id False --flag_full False \
--flag_visual True --flag_fml_5 True

python ./tfmatchd/face/test_unsupervise.py --mode test_one \
--dataset_dir /data/0_eccv2020_final/0_Benchmark_Server/32_AFLW2000_3D_tensor \
--output_dir /home/jshang/SHANG_Exp/ECCV2020/release_2020.07.10/0_local \
--ckpt_file /home/jshang/SHANG_Exp/ECCV2020/rebuttal_2020.04.04/final_model_main/70_21_warpdepth_reg/model-400000 \
--path_gpmm /home/jshang/SHANG_Data/ThirdLib/BFM2009/bfm09_dy_gyd_presplit.h5 \
--flag_mesh_id=False --flag_now=False --flag_full=False --flag_visual_origin=False --flag_visual_align=True --flag_eval=True
"""

def inverse_affine_warp_overlay(m_inv, image_ori, image_now, image_mask_now):
    from skimage import transform as trans
    tform = trans.SimilarityTransform(m_inv)
    M = tform.params[0:2, :]

    image_now_cv = cv2.cvtColor(image_now, cv2.COLOR_RGB2BGR)
    image_mask_now_cv = cv2.cvtColor(image_mask_now, cv2.COLOR_RGB2BGR)



    img_now_warp = cv2.warpAffine(image_now_cv, M, (image_ori.shape[1], image_ori.shape[0]), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_REPLICATE)
    image_mask_now_warp = cv2.warpAffine(image_mask_now_cv, M, (image_ori.shape[1], image_ori.shape[0]), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_REPLICATE)

    image_ori_back = (1.0 - image_mask_now_warp) * image_ori
    image_ori_back = image_ori_back.astype(np.uint8)
    image_ori_back = np.clip(image_ori_back, 0, 255)
    # if 1:
    #     cv2.imshow("Image Debug", image_ori_back)
    #     k = cv2.waitKey(0) & 0xFF
    #     if k == 27:
    #         cv2.destroyAllWindows()

    img_now_warp = img_now_warp * image_mask_now_warp
    img_now_warp = img_now_warp.astype(np.uint8)
    img_now_warp = np.clip(img_now_warp, 0, 255)

    img_replace = img_now_warp + image_ori_back
    img_replace = np.clip(img_replace, 0, 255)


    img_replace = img_replace.astype(np.uint8)
    img_replace = np.clip(img_replace, 0, 255)

    return img_replace

def parse_global_filelist(data_root, split, fmt=".jpg"):
    if 'test' in split:
        with open(data_root + '/%s' % split, 'r') as f:
            frames = f.readlines()
        name_subfolders = [x.split(' ')[0] for x in frames]
        name_images = [x.split(' ')[1][:-1] for x in frames]

        image_file_list = [os.path.join(data_root, name_subfolders[i], name_images[i] + fmt) for i in range(len(name_images))]
        return name_subfolders, image_file_list
    else:
        with open(data_root + '/%s' % split, 'r') as f:
            frames = f.readlines()
        name_subfolders = [x.split(' ')[1] for x in frames]
        name_images = [x.split(' ')[2][:-1] for x in frames]

        image_file_list = [os.path.join(data_root, name_subfolders[i], name_images[i] + fmt) for i in
                           range(len(name_images))]
        return name_subfolders, image_file_list

if __name__ == '__main__':

    path_global_list = os.path.join(FLAGS.dataset_dir, FLAGS.mode + '.txt')
    path_global_list_save = os.path.join(FLAGS.output_dir, FLAGS.mode + '.txt')

    name_subfolders, image_file_list = parse_global_filelist(FLAGS.dataset_dir, FLAGS.mode + '.txt', fmt=FLAGS.format_global_list)

    if not os.path.exists(FLAGS.dataset_dir):
        print("Error: no dataset_dir found")

    if not os.path.exists(FLAGS.output_dir):
        os.makedirs(FLAGS.output_dir)
    copyfile(path_global_list, path_global_list_save)
    print("Finish copy")

    """
    build graph
    """
    system = MGC_TRAIN(FLAGS)
    system.build_test_graph(
        FLAGS, img_height=FLAGS.img_height, img_width=FLAGS.img_width, batch_size=FLAGS.batch_size
    )

    """
    load model
    """
    IH = FLAGS.img_height
    IW = FLAGS.img_width

    test_var = tf.global_variables()#tf.model_variables()
    print('Global variables:')
    for var in test_var:
        print(var)
    test_var = [tv for tv in test_var if tv.op.name.find('VertexNormalsPreSplit') == -1]
    print('Testing variables:')
    for var in test_var:
        print(var)

    saver = tf.train.Saver([var for var in test_var])

    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    with tf.Session(config=config) as sess:
        sess.run(tf.global_variables_initializer())
        sess.graph.finalize()

        saver.restore(sess, FLAGS.ckpt_file)

        #
        list_pred_trimesh = []
        import time
        for t in range(0, len(image_file_list), FLAGS.batch_size):
            time_st = time.time()
            inputs = np.zeros(
                (FLAGS.batch_size, IH, IW, 3), dtype=np.uint8
            )
            for b in range(FLAGS.batch_size):
                idx = t + b
                if idx >= len(image_file_list):
                    break
                # if os.path.isfile(image_file_list[idx]) == False:
                #     continue
                path_image = image_file_list[idx]
                fh = open(path_image, 'r')
                image = pil.open(fh)
                scaled_image = image.resize((IW, IH), pil.ANTIALIAS)
                inputs[b] = np.array(image)

            """
            Start
            """
            pred = system.inference(sess, inputs)
            time_end = time.time()
            print("Time each batch: ", time_end - time_st)
            for b in range(FLAGS.batch_size):
                idx = t + b

                if idx >= len(image_file_list):
                    break
                print("Sample: (%d in %d) with %s" % (idx, len(image_file_list), name_subfolders[idx]))

                dic_subfolder_save = os.path.join(FLAGS.output_dir, name_subfolders[idx])
                if not os.path.exists(dic_subfolder_save):
                    os.makedirs(dic_subfolder_save)
                # if os.path.isfile(image_file_list[idx]) == False:
                #     continue
                dic_image, name_image = os.path.split(image_file_list[idx])
                name_image_pure, _ = os.path.splitext(name_image)

                print("Sample: (%d in %d) with %s" % (idx, len(image_file_list), name_subfolders[idx]))

                """
                Render
                """
                image_input = inputs[b]

                """
                NP
                """
                vertex_shape = pred['vertex_shape'][0][b, :, :]
                vertex_shape_id = pred['vertex_shape_id'][0][b, :, :]
                vertex_shape_full = pred['vertex_shape_full'][0][b, :, :]
                vertex_shape_id_full = pred['vertex_shape_id_full'][0][b, :, :]

                vertex_color = pred['vertex_color'][0][b, :, :][0]
                vertex_color = np.clip(vertex_color, 0, 1)
                vertex_color_ori = pred['vertex_color_ori'][0][b, :, :]
                vertex_color_ori_full = pred['vertex_color_ori_full'][0][b, :, :]
                vertex_color_ori = np.clip(vertex_color_ori, 0, 1)
                vertex_color_ori_full = np.clip(vertex_color_ori_full, 0, 1)

                if FLAGS.flag_eval:
                    if FLAGS.flag_now:
                        """
                        Mesh ID
                        """
                        mesh_tri_id = trimesh.Trimesh(
                            vertex_shape_id.reshape(-1, 3),
                            system.h_lrgp.h_curr.mesh_tri_np.reshape(-1, 3),
                            vertex_colors=vertex_color.reshape(-1, 3),
                            process=False
                        )
                        path_mesh_id_save = os.path.join(dic_subfolder_save, name_image_pure + ".obj")
                        mesh_tri_id.export(path_mesh_id_save)

                        """
                        Landmark 3D

                        """
                        idx_now_lm = [1314, 6341, 9832, 14714, 8200, 5520, 10537]
                        lm3d = vertex_shape_id[idx_now_lm]
                        path_lm3d_save = os.path.join(dic_subfolder_save, name_image_pure + ".txt")
                        write_NoW_lm(path_lm3d_save, lm3d, inter=' ')
                    else:
                        """
                        Mesh ID
                        """
                        if FLAGS.flag_mesh_id:
                            if FLAGS.flag_full:
                                mesh_tri_id = trimesh.Trimesh(
                                    vertex_shape_id_full.reshape(-1, 3),
                                    system.h_lrgp.h_full.mesh_tri_np.reshape(-1, 3),
                                    vertex_colors=vertex_color_ori_full.reshape(-1, 3),
                                    process=False
                                )
                                path_mesh_id_save = os.path.join(dic_subfolder_save, name_image_pure + "_id.ply")
                                mesh_tri_id.export(path_mesh_id_save)
                            else:
                                mesh_tri_id = trimesh.Trimesh(
                                    vertex_shape_id.reshape(-1, 3),
                                    system.h_lrgp.h_curr.mesh_tri_np.reshape(-1, 3),
                                    vertex_colors=vertex_color.reshape(-1, 3),
                                    process=False
                                )
                                path_mesh_id_save = os.path.join(dic_subfolder_save, name_image_pure + ".ply")
                                mesh_tri_id.export(path_mesh_id_save)

                        else:
                            if FLAGS.flag_full:
                                mesh_tri = trimesh.Trimesh(
                                    vertex_shape_full.reshape(-1, 3),
                                    system.h_lrgp.h_full.mesh_tri_np.reshape(-1, 3),
                                    vertex_colors=vertex_color_ori_full.reshape(-1, 3),
                                    process=False
                                )

                            else:
                                mesh_tri = trimesh.Trimesh(
                                    vertex_shape.reshape(-1, 3),
                                    system.h_lrgp.h_curr.mesh_tri_np.reshape(-1, 3),
                                    vertex_colors=vertex_color.reshape(-1, 3),
                                    process=False
                                )

                            path_mesh_save = os.path.join(dic_subfolder_save, name_image_pure + ".ply")
                            mesh_tri.export(path_mesh_save)
                        """
                        Landmark 3D

                        """
                        path_lm3d_save = os.path.join(dic_subfolder_save, name_image_pure + "_lm3d.txt")
                        lm_68 = vertex_shape[system.h_lrgp.h_curr.idx_lm68_np]

                        write_self_lm(path_lm3d_save, lm_68)

                        """
                        Landmark 2D

                        """
                        lm2d = pred['lm2d'][0][b, :, :]
                        path_lm2d_save = os.path.join(dic_subfolder_save, name_image_pure + "_lm2d.txt")
                        write_self_lm(path_lm2d_save, lm2d)

                        """
                        Pose
                        """
                        path_cam_save = os.path.join(dic_subfolder_save, name_image_pure + "_cam.txt")

                        pose = pred['gpmm_pose'][0][b, :]
                        intrinsic = pred['gpmm_intrinsic'][b, :, :]

                        write_self_camera(path_cam_save, FLAGS.img_width, FLAGS.img_height, intrinsic, pose)

                """
                Common visual
                """
                if FLAGS.flag_visual:
                    # visual
                    result_overlayMain_255 = pred['overlayMain_255'][0][b, :, :]
                    result_overlayTexMain_255 = pred['overlayTexMain_255'][0][b, :, :]
                    result_overlayGeoMain_255 = pred['overlayGeoMain_255'][0][b, :, :]
                    result_overlayLightMain_255 = pred['overlayLightMain_255'][0][b, :, :]
                    result_apper_mulPose_255 = pred['apper_mulPose_255'][0][b, :, :]

                    result_overlay_255 = pred['overlay_255'][0][b, :, :]
                    result_overlayTex_255 = pred['overlayTex_255'][0][b, :, :]
                    result_overlayGeo_255 = pred['overlayGeo_255'][0][b, :, :]
                    result_overlayLight_255 = pred['overlayLight_255'][0][b, :, :]

                    if FLAGS.flag_overlayOrigin_save:
                        gpmm_render_mask = pred['gpmm_render_mask'][0][b, :, :]
                        gpmm_render_mask = np.tile(gpmm_render_mask, reps=(1, 1, 3))

                        path_m_inv = os.path.join(dic_image, name_image_pure + "_tform.npy")
                        m_inv = np.load(path_m_inv)
                        path_image_origin = os.path.join(dic_image, name_image_pure + "_input.jpg")
                        image_origin = cv2.imread(path_image_origin)
                        # image_origin = pil.open(path_image_origin)
                        gpmm_render_overlay_wo = inverse_affine_warp_overlay(
                            m_inv, image_origin, result_overlay_255, gpmm_render_mask)
                        gpmm_render_overlay_texture_wo = inverse_affine_warp_overlay(
                            m_inv, image_origin, result_overlayTex_255, gpmm_render_mask)
                        gpmm_render_overlay_gary_wo = inverse_affine_warp_overlay(
                            m_inv, image_origin, result_overlayGeo_255, gpmm_render_mask)
                        gpmm_render_overlay_illu_wo = inverse_affine_warp_overlay(
                            m_inv, image_origin, result_overlayLight_255, gpmm_render_mask)

                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_overlayOrigin.jpg")
                        cv2.imwrite(path_image_save, gpmm_render_overlay_wo)
                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_overlayTexOrigin.jpg")
                        # cv2.imwrite(path_image_save, gpmm_render_overlay_texture_wo)
                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_overlayGeoOrigin.jpg")
                        cv2.imwrite(path_image_save, gpmm_render_overlay_gary_wo)
                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_overlayLightOrigin.jpg")
                        # cv2.imwrite(path_image_save, gpmm_render_overlay_illu_wo)


                    if FLAGS.flag_fml_5:
                        visual_concat = np.concatenate(
                            [image_input, result_overlay_255, result_overlayTex_255,
                             result_overlayGeo_255, result_overlayLight_255], axis=1)
                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_fml5_overlay.jpg")
                        plt.imsave(path_image_save, visual_concat)

                        visual_concat = np.concatenate(
                            [image_input, result_overlayMain_255, result_overlayTexMain_255,
                             result_overlayGeoMain_255, result_overlayLightMain_255], axis=1)
                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_fml5_main.jpg")
                        plt.imsave(path_image_save, visual_concat)

                        if FLAGS.flag_overlayOrigin_save:
                            visual_concat = np.concatenate(
                                [image_origin, gpmm_render_overlay_wo, gpmm_render_overlay_texture_wo,
                                 gpmm_render_overlay_gary_wo, gpmm_render_overlay_illu_wo], axis=1)
                            path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_fml5_origin.jpg")
                            cv2.imwrite(path_image_save, visual_concat)

                    # common
                    visual_concat = np.concatenate(
                        [image_input, result_overlay_255, result_overlayGeo_255, result_apper_mulPose_255], axis=1)
                    path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_mulPoses.jpg")
                    plt.imsave(path_image_save, visual_concat)

                    if FLAGS.flag_main_save:
                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_overlayMain.jpg")
                        plt.imsave(path_image_save, result_overlayMain_255)
                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_overlayTexMain.jpg")
                        # plt.imsave(path_image_gray_main_overlay, gpmm_render_overlay)
                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_overlayGeoMain.jpg")
                        plt.imsave(path_image_save, result_overlayGeoMain_255)
                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_overlayLightMain.jpg")
                        # cv2.imwrite(path_image_save, result_overlayLightMain_255)

                    if FLAGS.flag_overlay_save:
                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_overlay.jpg")
                        plt.imsave(path_image_save, result_overlay_255)
                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_overlayTex.jpg")
                        # cv2.imwrite(path_image_save, result_overlayTex_255)
                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_overlayGeo.jpg")
                        plt.imsave(path_image_save, result_overlayGeo_255)
                        path_image_save = os.path.join(dic_subfolder_save, name_image_pure + "_overlayLight.jpg")
                        # cv2.imwrite(path_image_save, result_overlayLight_255)

