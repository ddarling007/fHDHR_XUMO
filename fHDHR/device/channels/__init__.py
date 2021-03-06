import datetime
import time

from fHDHR.tools import hours_between_datetime, humanized_time

from .channel import Channel
from .chan_ident import Channel_IDs


class Channels():

    def __init__(self, fhdhr, originwrapper):
        self.fhdhr = fhdhr

        self.origin = originwrapper

        self.id_system = Channel_IDs(fhdhr)

        self.list = {}
        self.list_update_time = None

        self.get_db_channels()

    def get_channel_obj(self, keyfind, valfind):
        if keyfind == "number":
            return next(self.list[fhdhr_id] for fhdhr_id in list(self.list.keys()) if self.list[fhdhr_id].number == valfind) or None
        else:
            return next(self.list[fhdhr_id] for fhdhr_id in list(self.list.keys()) if self.list[fhdhr_id].dict[keyfind] == valfind) or None

    def get_channel_list(self, keyfind):
        if keyfind == "number":
            return [self.list[x].number for x in list(self.list.keys())]
        else:
            return [self.list[x].dict[keyfind] for x in list(self.list.keys())]

    def set_channel_status(self, keyfind, valfind, updatedict):
        self.get_channel_obj(keyfind, valfind).set_status(updatedict)

    def set_channel_enablement_all(self, enablement):
        for fhdhr_id in list(self.list.keys()):
            self.list[fhdhr_id].set_enablement(enablement)

    def set_channel_enablement(self, keyfind, valfind, enablement):
        self.get_channel_obj(keyfind, valfind).set_enablement(enablement)

    def set_channel_favorite(self, keyfind, valfind, enablement):
        self.get_channel_obj(keyfind, valfind).set_favorite(enablement)

    def get_db_channels(self):
        self.fhdhr.logger.info("Checking for Channel information stored in the database.")
        channel_ids = self.fhdhr.db.get_fhdhr_value("channels", "list") or []
        if len(channel_ids):
            self.fhdhr.logger.info("Found %s existing channels in the database." % str(len(channel_ids)))
        for channel_id in channel_ids:
            channel_obj = Channel(self.fhdhr, self.id_system, channel_id=channel_id)
            channel_id = channel_obj.dict["id"]
            self.list[channel_id] = channel_obj

    def get_channels(self, forceupdate=False):
        """Pull Channels from origin.

        Output a list.

        Don't pull more often than 12 hours.
        """

        updatelist = False
        if not self.list_update_time:
            updatelist = True
        elif hours_between_datetime(self.list_update_time, datetime.datetime.now()) > 12:
            updatelist = True
        elif forceupdate:
            updatelist = True

        if updatelist:
            channel_origin_id_list = [str(self.list[x].dict["origin_id"]) for x in list(self.list.keys())]

            self.fhdhr.logger.info("Performing Channel Scan.")

            channel_dict_list = self.origin.get_channels()
            self.fhdhr.logger.info("Found %s channels for %s." % (len(channel_dict_list), self.fhdhr.config.dict["main"]["servicename"]))

            self.fhdhr.logger.info("Performing Channel Import, This can take some time, Please wait.")

            newchan = 0
            chan_scan_start = time.time()
            for channel_info in channel_dict_list:

                chan_existing = False
                if str(channel_info["id"]) in channel_origin_id_list:
                    chan_existing = True
                    channel_obj = self.get_channel_obj("origin_id", channel_info["id"])
                else:
                    channel_obj = Channel(self.fhdhr, self.id_system, origin_id=channel_info["id"])

                channel_id = channel_obj.dict["id"]
                channel_obj.basics(channel_info)
                if not chan_existing:
                    self.list[channel_id] = channel_obj
                    newchan += 1

            self.fhdhr.logger.info("Channel Import took %s" % humanized_time(time.time() - chan_scan_start))

            if not newchan:
                newchan = "no"
            self.fhdhr.logger.info("Found %s NEW channels." % newchan)

            self.fhdhr.logger.info("Total Channel Count: %s" % len(self.list.keys()))

            self.list_update_time = datetime.datetime.now()
            self.fhdhr.db.set_fhdhr_value("channels", "scanned_time", time.time())

        channel_list = []
        for chan_obj in list(self.list.keys()):
            channel_list.append(self.list[chan_obj].dict)
        return channel_list

    def get_channel_stream(self, channel_number):
        return self.origin.get_channel_stream(self.get_channel_dict("number", channel_number))

    def get_channel_dict(self, keyfind, valfind):
        return self.get_channel_obj(keyfind, valfind).dict
