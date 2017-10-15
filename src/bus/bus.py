#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class Bus(object):
    async def start(self):
        raise NotImplementedError()

    async def req(self, path, timeout):
        raise NotImplementedError()

    async def reg_rep(self, path, callback):
        raise NotImplementedError()

    async def pub(self, path, payload):
        raise NotImplementedError()

    async def reg_sub(self, path, callback):
        raise NotImplementedError()
