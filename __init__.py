# coding=utf-8
import logging

logger = logging.getLogger(__name__)
hdlr = logging.NullHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.INFO)
