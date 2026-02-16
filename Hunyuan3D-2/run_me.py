import sys
from pathlib import Path
sys.path.insert(0, '/content/Hunyuan3D-2/')
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

# Get the absolute path of the script (backend_servo.py)
SCRIPT_DIR = Path(__file__).resolve().parent

# Get the project root (Go up one level from Hunyuan3D-2)
PROJECT_ROOT = SCRIPT_DIR.parent


# Use the absolute path to the parent folder of 'hunyuan3d-dit-v2-0'
pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(f'{PROJECT_ROOT}/Hunyuan3D-2')

def img_to_3d(img_name,name_without_ext=""):
    """
    Takes img name and pick that image from the static/processed folder
    converts it to 3d model-> .stl and .glb
    saves it at static/meshes folder
    :param img_name:
    :param name_without_ext:
    :return:
    """

    input_path = PROJECT_ROOT / 'static' / 'processed' / img_name
    mesh = pipeline(image=str(input_path))[0]

    if name_without_ext == '':
        name_without_ext = Path(img_name).stem

    # Construct output paths
    output_glb = PROJECT_ROOT / 'static' / 'meshes' / f'{name_without_ext}.glb'
    output_stl = PROJECT_ROOT / 'static' / 'meshes' / f'{name_without_ext}.stl'

    # Create directory if it doesn't exist
    output_glb.parent.mkdir(parents=True, exist_ok=True)

    mesh.export(str(output_glb))
    print(f"glb exported to {output_glb}")

    mesh.export(str(output_stl))
    print(f"stl exported to {output_stl}")

    return True


# img_name = "Female-Titan-removebg.png"
# img_to_3d(img_name)





                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          