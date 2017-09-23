"""@package PKD_Tools.libCrypto
@brief Simple API to encrypt and decrypt strings using Vigenere cipher

http://stackoverflow.com/questions/2490334/simple-way-to-encode-a-string-according-to-a-password/16321853#16321853
"""

import base64
import struct
import zlib


def encode(text, key):
    """
    Encode the string based on a user defined key
    @param text: (string) The text that is being encode
    @param key: (string) Special code that is used to help encode the text. This should match whe we decode
    @return: The encoded text
    """
    text = '{}{}'.format(text, struct.pack('i', zlib.crc32(text)))
    enc = []
    for i in range(len(text)):
        key_c = key[i % len(key)]
        enc_c = chr((ord(text[i]) + ord(key_c)) % 256)
        enc.append(enc_c)

    return base64.urlsafe_b64encode("".join(enc))


def decode(encodedText, key):
    """
    Deccode a encoded string based on a user defined key
    @param encodedText: (string) The text we need to decode
    @param key: (string) The text that used to code the string
    @return (string): The decoded text
    """
    dec = []
    encodedText = base64.urlsafe_b64decode(encodedText)
    for i in range(len(encodedText)):
        key_c = key[i % len(key)]
        dec_c = chr((256 + ord(encodedText[i]) - ord(key_c)) % 256)
        dec.append(dec_c)

    dec = "".join(dec)
    checksum = dec[-4:]
    dec = dec[:-4]

    assert zlib.crc32(dec) == struct.unpack('i', checksum)[0], 'Decode Checksum Error'

    return dec
