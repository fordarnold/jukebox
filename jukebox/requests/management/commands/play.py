from django.core.management.base import BaseCommand, CommandError
import datetime
from optparse import make_option
from requests.models import Request, Vote
from tracks.models import Track
from subprocess import call
import sys
import os
from time import sleep
from django.contrib.auth.models import User
import redis

class Command(BaseCommand):
    option_list = BaseCommand.option_list
    
    def handle(self, *args, **options):
        user = User.get_anonymous()
        r = redis.StrictRedis(host='localhost', port=6379, db=1)

        while(True):
            try:
                playlist = Request.objects.filter(status='Q').order_by('created_on')
                
                for request in playlist:
                    request.status = 'P'
                    request.played_on = datetime.datetime.now()
                    request.save()

                    # clear our request cache
                    r.delete(":1:request_list")

                    # and our now playing
                    r.delete(":1:playlist")
                    
                    try:                            
                        call(["mpg123", request.track.mp3_file.path])
                    except:
                        import traceback
                        traceback.print_exc()
                        sys.exit(1)
                    finally:
                        request.status = 'C'
                        request.save()
                    
                if not playlist:
                    # find all songs that have been requested by real users
                    requests = Request.objects.exclude(created_by_id=-1)

                    # now exclude any song that has ever been voted down
                    requests = requests.exclude(track_id__in=[t.track_id for t in Vote.objects.filter(score=-1)])

                    # exclude anything that has been played recently
                    window = datetime.datetime.now() - datetime.timedelta(hours=6)
                    requests = requests.exclude(track_id__in=[t.track_id for t in Request.objects.filter(created_on__gt=window)])

                    if requests:
                        requests = requests.order_by('?')
                        Request.objects.create(track=requests[0].track,
                                               created_by=user,
                                               modified_by=user,
                                               played_on=None)
                        
                    # for the bug of tracks stucking on the playing status because of an unxpected system halt 
                    request_completed = Request.objects.filter(status='P').order_by('created_on')
                    for req in request_completed:
                        if long((datetime.datetime.now() - req.played_on).total_seconds()) > req.track.length:
                            req.status = 'C'
                            req.save()

            except:
                import traceback
                traceback.print_exc()
                sys.exit(1)


            
                    
            
