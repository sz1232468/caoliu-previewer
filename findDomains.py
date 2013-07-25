#!/usr/bin/env python

"""Query domain names by ipaddr
   Requriment: pyquery
"""

try:
  from pyquery import PyQuery as pq
except ImportError:
  raise Exception("pyquery module is required. You can install pyquery with pip")

import urllib
import re
import sys
import socket
import threading
import gflags

class DNSReverse(object):
  BASE = "http://dns.aizhan.com/"
  url = None
  def __init__(self, ipaddr = None, page = None, url = None):
    self.domains = []
    query = {}
    if ipaddr != None: query['q'] = ipaddr
    if page != None: query['page'] = page

    if len(query) > 0:
      self.url = self.BASE + '?' + urllib.urlencode(query)
    else:
      self.url = self.BASE + url


  def __call__(self, recursive = True):
    if not self.url:
      raise Exception('url empty')
    sys.stderr.write('Querying page %s\n' % self.url)

    doc = pq(url=self.url)
    for elem in doc('input'):
      eid = elem.attrib.get('id', None)
      val = elem.attrib.get('value', None)
      if eid and re.match(r'^domain\d+$', eid.strip(), re.I) and val:
        if re.match(r'^[0-9a-z\-\.]+$', val.strip()):
          self.domains.append(val)

    # pagenation
    if recursive:
      hrefs = []
      for anchor in doc('.page a'):
        href = anchor.attrib.get('href', None)
        if href: hrefs.append(href)
      for href in set(hrefs):
        self.domains += self.__class__(url = href)(recursive = False)

    return list(set(self.domains))

def checkDomain(total_domains):
  availURIs = []
  threads = []
  for domain in total_domains:
    def target(domain, availURIs):
      try:
        sys.stderr.write('Verifying %s\n' % domain)
        sys.stderr.flush()
        socket.getaddrinfo(domain, 80)
        availURIs.append("http://%s/*" % domain)
      except socket.gaierror:
        sys.stderr.write('Domain %s is unreachable.\n' % domain)

    thread = threading.Thread(target = target, args = (domain, availURIs))
    threads.append(thread)
    thread.start()

  for thread in threads:
    thread.join()


FLAGS = gflags.FLAGS

gflags.DEFINE_bool('apply_to_manifest',
    False, "Apply the domains to the manifest.", short_name = 'm')

gflags.DEFINE_bool('write_into_file',
    False, "Write into latestDomains.txt", short_name = 'w')

def main(argv):
  try:
    argv = FLAGS(argv)
  except gflags.FlagsError, e:
    sys.stderr.write('%s\nUsage: %s ARGS\n%s' % (e, argv[0], FLAGS))
    sys.exit(1)

  ips = ['184.154.128.243',
      '184.154.128.244',
      '184.154.128.245',
      '184.154.128.246']

  total_domains = []
  for ip in ips:
    domains = DNSReverse(ipaddr = ip)()
    sys.stderr.write("Domains of %s: %s\n" % (ip, domains))
    total_domains += domains

  total_domains += ips
  total_domains = list(set(total_domains))
  total_domains.sort()

  availURIs = ['"http://%s/*"' % domain for domain in total_domains]

  sys.stderr.write("Caoliu domains: \n")
  output = ',\n'.join(availURIs)

  if FLAGS.write_into_file:
    with open('latestDomains.txt', 'w') as f:
      f.write(output)
  else:
    sys.stdout.write(output)

  if FLAGS.apply_to_manifest:
    with open('manifest.json', 'r+') as f:
      content = f.read()
      result = re.search(r'matches.*?\[(.*?)\]',
          content,
          re.DOTALL|re.MULTILINE)

      repl = '\n' + ',\n'.join([(" " * 6 + uri) for uri in availURIs])
      content = content[:result.start(1)] + repl + content[result.end(1):]

      f.seek(0, 0); f.truncate();
      f.write(content)

if __name__ == '__main__':
  main(sys.argv)


