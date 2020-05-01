"""
Author: Metehan Cekic
Random + Fast Gradient Sign Method
"""

import torch
import torchvision
from torch import nn


def RFGSM(net, x, y_true, data_params, attack_params):
    """
    Description: Random + Fast Gradient Sign Method
    Input :
        net : Neural Network            (torch.nn.Module)
        x : Inputs to the net           (Batch)
        y_true : Labels                 (Batch)
        data_params :
            x_min:  Minimum possible value of x (min pixel value)   (Float)
            x_max:  Maximum possible value of x (max pixel value)   (Float)
        attack_params :
            norm:   Attack norm         (Str)
            eps:    Attack budget       (Float)
            alpha:  Attack step size    (Float)
    Output:
        perturbation : Single step perturbation (Clamped with input limits)

    Explanation:
        e = uniform(-eps,eps)
        e += alpha * sign(grad_{x}(net(x)))
        clip(e, -eps, eps)
    """
    if attack_params["norm"] == "inf":
        e = torch.rand_like(x) * 2 * attack_params['eps'] - attack_params['eps']
    else:
        e = 2 * torch.rand_like(x) - 1
        e = e * attack_params["eps"] / \
            e.view(x.shape[0], -1).norm(p=int(attack_params["norm"]), dim=-1).view(-1, 1, 1, 1)

    # Clip perturbation before gradient calculation to get best performance
    e.data = torch.max(torch.min(e, data_params["x_max"] - x), data_params["x_min"] - x)
    e.requires_grad = True

    y_hat = net(x + e)

    # Loss computation
    criterion = nn.CrossEntropyLoss(reduction="none")
    loss = criterion(y_hat, y_true)

    # Calculating backprop for images
    loss.backward(gradient=torch.ones_like(y_true, dtype=torch.float), retain_graph=True)
    e_grad = e.grad.data

    if attack_params["norm"] == "inf":
        perturbation = torch.clamp(
            e + attack_params['alpha'] * e_grad.sign(), -attack_params['eps'], attack_params['eps'])
    else:
        perturbation = (e + e_grad * attack_params['alpha']) / \
            (e+e_grad).view(e.shape[0], -1).norm(p=attack_params["norm"], dim=-1).view(-1, 1, 1, 1)

    # Clipping perturbations so that  x_min < image + perturbation < x_max
    perturbation.data = torch.max(
        torch.min(perturbation, data_params["x_max"] - x), data_params["x_min"] - x)

    return perturbation