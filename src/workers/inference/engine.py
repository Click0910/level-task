import os
import torch
from typing import List

from celery.utils.log import get_logger

from utils.dataset import ImagesDataset


DATA_FOLDER = os.getenv("DATA_FOLDER", "")

logger = get_logger(__name__)


class TicketInference:
    """
    To Do
    """
    pass
