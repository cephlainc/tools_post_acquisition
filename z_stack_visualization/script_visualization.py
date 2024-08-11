import numpy as np
import napari
from tifffile import imread
import os
import json
from vispy.color import Colormap

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

def import_layer_settings(viewer, folder_path):
    filepath = os.path.join(folder_path, 'layer_settings.json')
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            layer_settings = json.load(f)
        
        for layer in viewer.layers:
            if isinstance(layer, napari.layers.Image) and layer.name in layer_settings:
                settings = layer_settings[layer.name]
                layer.colormap = settings['colormap']
                layer.contrast_limits = settings['contrast_limits']

def export_layer_settings(viewer, folder_path):
    layer_settings = {}
    for layer in viewer.layers:
        if isinstance(layer, napari.layers.Image):
            layer_settings[layer.name] = {
                'colormap': layer.colormap.name,
                'contrast_limits': layer.contrast_limits
            }
    
    filepath = os.path.join(folder_path, 'layer_settings.json')
    with open(filepath, 'w') as f:
        json.dump(layer_settings, f, indent=2)

def bin_image(image, binning_factor):
    height, width = image.shape
    height = height - (height % binning_factor)
    width = width - (width % binning_factor)
    image = image[:height, :width]
    
    reshaped_image = image.reshape((height // binning_factor, binning_factor,
                                    width // binning_factor, binning_factor))
    binned_image = reshaped_image.mean(axis=(1, 3))
    return binned_image

def crop_center(image, crop_size):
    height, width = image.shape[:2]
    left = (width - crop_size) // 2
    top = (height - crop_size) // 2
    right = left + crop_size
    bottom = top + crop_size
    return image[top:bottom, left:right]

def parse_filename(filename):
    parts = filename.split('_')
    z_index = int(parts[3])
    channel = '_'.join(parts[5:8]).rstrip('.tiff')
    return z_index, channel

def load_acquisition_parameters(folder_path):
    param_file = os.path.join(folder_path, 'acquisition parameters.json')
    with open(param_file, 'r') as f:
        params = json.load(f)
    return params

def load_and_process_images(folder_path, xy_binning=1, z_downsample=1, z_range=None, crop_size=None):
    image_folder = os.path.join(folder_path, '0')
    tiff_files = [f for f in os.listdir(image_folder) if f.endswith(('.tiff', '.tif')) and not f.startswith('._')]
    
    channels = set()
    z_indices = set()
    for filename in tiff_files:
        z, channel = parse_filename(filename)
        channels.add(channel)
        z_indices.add(z)
    
    z_indices = sorted(z_indices)
    
    if z_range:
        start, end = z_range
        z_indices = [z for z in z_indices if start <= z < end]
    
    z_indices = z_indices[::z_downsample]
    print(z_indices)
    
    # Read one image to get dimensions
    sample_image = imread(os.path.join(image_folder, tiff_files[0]))
    if crop_size:
        sample_image = crop_center(sample_image, crop_size)
    y_dim, x_dim = sample_image.shape
    y_dim = y_dim // xy_binning
    x_dim = x_dim // xy_binning
    
    image_stacks = {channel: np.zeros((len(z_indices), y_dim, x_dim), dtype=np.float32) for channel in channels}
    
    for idx, z in enumerate(z_indices):
        for channel in channels:
            filename = next((f for f in tiff_files if parse_filename(f) == (z, channel)), None)
            if filename:
                filepath = os.path.join(image_folder, filename)
                image = imread(filepath)
                if crop_size:
                    image = crop_center(image, crop_size)
                if xy_binning > 1:
                    image = bin_image(image, xy_binning)
                image_stacks[channel][idx] = image
            else:
                print(f"Warning: Missing file for z={z}, channel={channel}")
    
    return image_stacks

def visualize_stacks(image_stacks, xy_binning, z_downsample, acquisition_params, folder_path):
    colormaps = {
        "561_nm_Ex": Colormap(['black', '#FFCF00']),
        "488_nm_Ex": Colormap(['black', '#1FFF00']),
        "405_nm_Ex": Colormap(['black', '#3300FF']),
        "638_nm_Ex": Colormap(['black', '#FF0000']),
    }

    original_z_spacing = acquisition_params['dz(um)']
    sensor_pixel_size = acquisition_params['sensor_pixel_size_um']
    magnification = acquisition_params['objective']['magnification']
    
    pixel_size = (sensor_pixel_size / magnification) * xy_binning
    z_spacing = original_z_spacing * z_downsample

    z_dim, y_dim, x_dim = next(iter(image_stacks.values())).shape
    bounding_box = np.array([
        [0, 0, 0],
        [0, y_dim * pixel_size, 0],
        [0, y_dim * pixel_size, x_dim * pixel_size],
        [0, 0, x_dim * pixel_size],
        [z_dim * z_spacing, 0, 0],
        [z_dim * z_spacing, y_dim * pixel_size, 0],
        [z_dim * z_spacing, y_dim * pixel_size, x_dim * pixel_size],
        [z_dim * z_spacing, 0, x_dim * pixel_size]
    ])

    edges = [
        [bounding_box[0], bounding_box[1]],
        [bounding_box[1], bounding_box[2]],
        [bounding_box[2], bounding_box[3]],
        [bounding_box[3], bounding_box[0]],
        [bounding_box[4], bounding_box[5]],
        [bounding_box[5], bounding_box[6]],
        [bounding_box[6], bounding_box[7]],
        [bounding_box[7], bounding_box[4]],
        [bounding_box[4], bounding_box[0]],
        [bounding_box[1], bounding_box[5]],
        [bounding_box[6], bounding_box[2]],
        [bounding_box[3], bounding_box[7]]
    ]
    edges = np.array([item for sublist in edges for item in sublist])

    viewer = napari.Viewer()

    for channel, stack in image_stacks.items():
        print(stack.shape)
        viewer.add_image(
            stack,
            scale=(z_spacing, pixel_size, pixel_size),
            name=channel,
            colormap=colormaps[channel],
            blending='additive'
        )

    import_layer_settings(viewer, folder_path)

    '''
    viewer.add_shapes(
        edges,
        shape_type='path',
        edge_color='white',
        name='Bounding Box',
        blending='translucent',
        face_color='transparent',
        edge_width=0.2
    )
    '''

    napari.run()

# This function will be called from the GUI
def run_visualization(folder_path, xy_binning, z_downsample, z_range, crop_size):
    acquisition_params = load_acquisition_parameters(folder_path)
    image_stacks = load_and_process_images(folder_path, xy_binning, z_downsample, z_range, crop_size)
    visualize_stacks(image_stacks, xy_binning, z_downsample, acquisition_params, folder_path)

if __name__ == "__main__":
    # This part is for testing purposes and won't be used when called from the GUI
    folder_path = "path/to/selected/folder"
    xy_binning = 1
    z_downsample = 1
    z_range = None
    crop_size = None
    run_visualization(folder_path, xy_binning, z_downsample, z_range, crop_size)
