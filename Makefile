#
# Freevo main makefile
# 
# $Id$
#

SUBDIRS = matrox_g400 rc_client osd_server

all: subdirs runapp

x11: all osds_x11

sdl: all osds_sdl

.PHONY: all subdirs x11 osd_x1 $(SUBDIRS) clean release install

osds_x11:
	cd osd_server ; $(MAKE) osds_x11

osds_sdl:
	cd osd_server ; $(MAKE) osds_sdl

runapp:
	gcc -o runapp runapp.c -DRUNAPP_LOGDIR=\"/var/log/freevo\"

subdirs: $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) -C $@

clean:
	-rm -f *.pyc *.o log_main_out log_main_err log.txt runapp
	cd matrox_g400 ; make clean
	cd rc_client ; make clean
	cd osd_server ; make clean


# XXX Real simple install procedure for now, but freevo is so small it doesn't really
# XXX matter
install: all
	-mv /usr/local/freevo /usr/local/freevo_old_`date +%Y%m%d_%H%M%S`
	-rm -rf /usr/local/freevo
	-mkdir /usr/local/freevo

	-mkdir -p /var/log/freevo
	chmod ugo+rwx /var/log/freevo

	-mkdir -p /var/cache/freevo
	chmod ugo+rwx /var/cache/freevo

	-mkdir -p /var/cache/xmltv/logos
	chmod -R ugo+rwx /var/cache/xmltv

	cp -r * /usr/local/freevo
