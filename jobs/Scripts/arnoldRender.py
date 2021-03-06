import argparse
import sys
import os
import subprocess
import psutil
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import main_logger
from jobs_launcher.core.config import RENDER_REPORT_BASE
import cpuinfo

def createArgsParser():
    parser = argparse.ArgumentParser()

    parser.add_argument('--tests_list', required=True, metavar="<path>")
    parser.add_argument('--render_path', required=True, metavar="<path>")
    parser.add_argument('--scene_path', required=True, metavar="<path")
    parser.add_argument('--output_dir', required=True)
    parser.add_argument('--output_img_dir', required=True)
    parser.add_argument('--output_file_ext', required=True)
    return parser


def main():
    args = createArgsParser().parse_args()

    tests_list = {}
    with open(args.tests_list, 'r') as file:
        tests_list = json.loads(file.read())

    try:
        os.makedirs(args.output_img_dir)
    except OSError as err:
        main_logger.error(str(err))
        return 1

    for test in tests_list:
        if test['status'] == 'active':
            case_report = RENDER_REPORT_BASE
            case_report.update({
                "original_color_path": "Color/" + test['name'] + '.' + args.output_file_ext,
                "original_render_log": test['name'] + '.or.log',
                "render_device": cpuinfo.get_cpu_info()['brand']
            })

            render_log_path = os.path.join(args.output_dir, test['name'] + '.or.log')
            case_camera = "persp"
            if "camera" in test.keys() and test['camera']:
                case_camera = test['camera']
            cmd_script = '"{render_path}" -r arnold -log "{log_path}" -rd "{out_dir}" -cam {camera} -im "{img_name}" -of {file_ext} "{scene_path}"'\
                .format(render_path=args.render_path, log_path=render_log_path, out_dir=args.output_img_dir,
                        camera=case_camera, img_name=test['name'], file_ext=args.output_file_ext, scene_path=os.path.join(args.scene_path, test['name']))
            cmd_script_path = os.path.join(args.output_dir, test['name'] + '.renderArnold.bat')

            try:
                with open(cmd_script_path, 'w') as file:
                    file.write(cmd_script)
                with open(render_log_path, 'w') as file:
                    pass
            except OSError as err:
                main_logger.error("Error while saving bat: {}".format(str(err)))
            else:
                rc = -1
                os.chdir(args.output_dir)
                p = psutil.Popen(cmd_script_path, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = p.communicate()

                try:
                    rc = p.wait()
                except psutil.TimeoutExpired as err:
                    main_logger.error("Terminated by simple render. {}".format(str(err)))
                    rc = -1
                    for child in reversed(p.children(recursive=True)):
                        child.terminate()
                    p.terminate()
                # return rc
                if rc == 0:
                    with open(os.path.join(args.output_dir, test['name'] + '_AI.json'), 'w') as file:
                        json.dump([case_report], file, indent=4)
    return 0


if __name__ == "__main__":
    exit(main())
