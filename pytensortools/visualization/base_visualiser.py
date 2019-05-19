from abc import ABC, abstractmethod
from .. import visualization
from ..evaluation.base_evaluator import BaseEvaluator
import pytensor
import matplotlib.pyplot as plt
import numpy as np
import string
import matplotlib as mpl

from plottools.fMRI.tile_plots import create_fmri_factor_plot
import plottools

mpl.rcParams['font.family'] = 'PT Sans'

def create_visualiser(visualiser_params, summary):
    Visualiser = getattr(visualization, visualiser_params['type'])
    kwargs = visualiser_params.get('arguments', {})
    return Visualiser(summary=summary, **kwargs)


def create_visualisers(visualisers_params, summary):
    visualisers = []
    for visualiser_params in visualisers_params:
        visualisers.append(create_visualiser(visualiser_params, summary))
    return visualisers


class BaseVisualiser(BaseEvaluator):
    figsize = (5.91, 3.8)
    _name = 'visualisation'
    def __init__(self, summary, filename=None, figsize=None):
        self.summary = summary
        self.DecomposerType = getattr(pytensor.decomposition, summary['model_type'])
        self.DecompositionType = self.DecomposerType.DecompositionType

        if figsize is not None:
            self.figsize = figsize
        
        if filename is not None:
            self._name = filename

    def __call__(self, data_reader, h5):
        return self._visualise(data_reader, h5)

    @abstractmethod
    def _visualise(self, data_reader, h5):
        pass

    def create_figure(self, *args, **kwargs):
        return plt.figure(*args, figsize=self.figsize, **kwargs)

class FactorLinePlotter(BaseVisualiser):
    _name = 'factor_lineplot'
    def __init__(self, summary, modes, normalise=True, labels=None, show_legend=True, filename=None, figsize=None):
        super().__init__(summary=summary, filename=filename, figsize=figsize)
        self.modes = modes
        self.figsize = (self.figsize[0]*len(modes), self.figsize[1])
        self.labels = labels
        self.show_legend = show_legend
        self.normalise = normalise

    def _visualise_mode(self, data_reader, factor_matrices, ax, mode, label=None,):
        factor = factor_matrices[mode]
        
        if self.normalise:
            factor = factor/np.linalg.norm(factor, axis=0, keepdims=True)

        ax.plot(factor)
        ax.set_title(f'Mode {mode}')
        if (data_reader.mode_names is not None) and (len(data_reader.mode_names) > mode):
            ax.set_title(data_reader.mode_names[mode])

        ax.set_xlabel(label)
        
        if self.show_legend:
            letter = string.ascii_lowercase[mode]
            ax.legend([f'{letter}{i}' for i in range(factor.shape[1])], loc='upper right')


    def _visualise(self, data_reader, h5):
        fig = self.create_figure()
        factor_matrices = self.load_final_checkpoint(h5)

        num_cols = len(self.modes)
        for i, mode in enumerate(self.modes):
            ax = fig.add_subplot(1, num_cols, i+1)

            label = None
            if self.labels is not None:
                label = self.labels[i]

            self._visualise_mode(data_reader, factor_matrices, ax, mode, label=label)

        return fig

class ClassLinePlotter(BaseVisualiser):
    _name = 'ClassLinePlotter'

    def __init__(self, summary, mode, class_name, filename=None, figsize=None):
        super().__init__(summary=summary, filename=filename, figsize=figsize)
        self.mode = mode
        self.class_name = class_name
    
    def _visualise(self, data_reader, h5):
        fig = self.create_figure()
        ax = fig.add_subplot(111)
        factor_matrices = self.load_final_checkpoint(h5)

        ax.plot(factor_matrices[self.mode])
        ylim = ax.get_ylim()

        classes = data_reader.classes[self.mode][self.class_name].squeeze()
        unique_classes = np.unique(classes)
        class_id = {c: i for i, c in enumerate(np.unique(classes))}
        classes = np.array([class_id[c] for c in classes])

        diff = classes[1:] - classes[:-1]
        for i, di in enumerate(diff):
            if di != 0:
                ax.plot([i + 0.5, i + 0.5], ylim, 'r')
        
        ax.set_ylim(ylim)
        return fig


# TODO: BaseSingleComponentPlotter
class SingleComponentLinePlotter(BaseVisualiser):
    _name = "single_factor_lineplot"
    def __init__(self, summary, mode, normalise=True, common_axis=True, label=None, filename=None, figsize=None):
        super().__init__(summary=summary, filename=filename, figsize=figsize)
        self.mode = mode
        self.normalise = normalise
        self.label = label
        self.common_axis = common_axis
        self.figsize = (self.figsize[0]*summary['model_rank']*0.7, self.figsize[1])
    
    def _visualise(self, data_reader, h5):
        fig = self.create_figure()
        factor = self.load_final_checkpoint(h5)[self.mode]
        rank = factor.shape[1]

        if self.normalise:
            factor = factor/np.linalg.norm(factor, axis=0, keepdims=True)

        self.figsize = (self.figsize[0]*rank, self.figsize[1])


        for r in range(rank):
            ax = fig.add_subplot(1, rank, r+1)

            ax.plot(factor[:, r])
            
            if (data_reader.mode_names is not None) and len(data_reader.mode_names) > self.mode:
                ax.set_xlabel(data_reader.mode_names[self.mode])
            if self.label is not None:
                ax.set_xlabel(self.label)
            
            if r == 0:
                ax.set_ylabel('Factor')
            
            ax.set_title(f'Component {r}')

        return fig

class FactorScatterPlotter(BaseVisualiser):
    """Note: only works for two classes"""
    _name = 'factor_scatterplot'
    def __init__(self, summary, mode, class_name, normalise=True, common_axis=True, label=None, legend=None, filename=None, figsize=None):
        super().__init__(summary=summary, filename=filename, figsize=figsize)
        self.mode = mode
        self.normalise = normalise
        self.label = label
        self.legend = legend
        self.common_axis = common_axis
        self.class_name = class_name
        self.figsize = (self.figsize[0]*summary['model_rank']*0.7, self.figsize[1])

    def _visualise(self, data_reader, h5):
        fig = self.create_figure()
        factor = self.load_final_checkpoint(h5)[self.mode]
        rank = factor.shape[1]

        if self.normalise:
            factor = factor/np.linalg.norm(factor, axis=0, keepdims=True)

        self.figsize = (self.figsize[0]*rank, self.figsize[1])

        x_values = np.arange(factor.shape[0])

        classes = data_reader.classes[self.mode][self.class_name].squeeze()

        #assert len(set(classes)) == 2

        different_classes = np.unique(classes)
        class1 = different_classes[0]
        class2 = different_classes[1]

        for r in range(rank):
            ax = fig.add_subplot(1, rank, r+1)

            for c in different_classes:
                ax.scatter(x_values[classes==c], factor[classes==c, r], label=c)
            
            #ax.scatter(x_values[classes==class1], factor[classes==class1, r], color='tomato')
            #ax.scatter(x_values[classes==class2], factor[classes==class2, r], color='darkslateblue')
            
            if (data_reader.mode_names is not None) and len(data_reader.mode_names) > self.mode:
                ax.set_xlabel(data_reader.mode_names[self.mode])
            if self.label is not None:
                ax.set_xlabel(self.label)
            
            if r == 0:
                ax.set_ylabel('Factor')
            elif self.common_axis:
                ax.set_yticks([])
            
            ax.set_title(f'Component {r}')

            if self.common_axis:
                fmin = factor.min()
                fmax = factor.max()
                df = fmax - fmin
                ax.set_ylim(fmin - 0.01*df, fmax + 0.01*df)

            if self.legend is not None: 
                ax.legend(self.legend)
            else:
                ax.legend()

        return fig


class LogPlotter(BaseVisualiser):
    _name = 'logplot'
    def __init__(self, summary, logger_name, log_name=None, filename=None, figsize=None,):
        super().__init__(summary=summary, filename=filename, figsize=figsize)
        self.logger_name = logger_name
        self.log_name = log_name
    
    def _visualise(self, data_reader, h5):
        its = h5[f'{self.logger_name}/iterations'][...]
        values = h5[f'{self.logger_name}/values'][...]

        fig = self.create_figure()
        ax = fig.add_subplot(111)
        ax.plot(its, values)
        ax.set_xlabel('Iteration')
        ax.set_ylabel('Value')
        ax.set_title(self.log_name)

        return fig

class FactorfMRIImage(BaseVisualiser):
    def __init__(
        self, 
        summary, 
        mode, 
        mask_path,
        template_path,
        filename=None, 
        figsize=None, 
        tile_plot_kwargs=None
        ):

        super().__init__(summary=summary, filename=filename, figsize=figsize)
        self.mode = mode
        self.tile_plot_kwargs = tile_plot_kwargs
        self.mask_path = mask_path
        self.template_path = template_path
        if figsize is None:
            figsize = (self.figsize[0]*summary['model_rank']*0.7, self.figsize[1])
        self.figsize = figsize

    def _visualise(self, data_reader, h5):
        factor = self.load_final_checkpoint(h5)[self.mode]

        mask = plottools.fMRI.base.load_mask(self.mask_path)
        template = plottools.fMRI.base.load_template(self.template_path)

        fmri_factor = plottools.fmri.base.get_fMRI_images(factor, mask, axis=0)
        fig, axes = plt.subplots(1, self.summary['model_rank'], figsize=self.figsize)
        for i, ax in enumerate(axes):
            create_fmri_factor_plot(fmri_factor[:, i], template, ax=ax, **self.tile_plot_kwargs)
        return fig

    
