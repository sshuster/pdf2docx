# -*- coding: utf-8 -*-

'''
A group of instances, e.g. instances, Spans, Shapes.

@created: 2020-07-24
@author: train8808@gmail.com
'''

from .BBox import BBox
from .base import IText, TextDirection
from .utils import graph_BFS


class BaseCollection:
    '''Base collection of specific instances.'''
    def __init__(self, instances:list=[]):
        '''Init collection from a list of BBox instances.'''
        self._instances = instances if instances else [] # type: list[BBox]

    def __getitem__(self, idx):
        try:
            instances = self._instances[idx]
        except IndexError:
            msg = f'Collection index {idx} out of range'
            raise IndexError(msg)
        else:
            return instances

    def __iter__(self): return (instance for instance in self._instances)

    def __len__(self): return len(self._instances)


    def group(self, fun):
        ''' Group instances according to user defined criterion.
            ---
            Args:
            - fun: function with 2 arguments representing 2 instances (BBox), and return bool
            
            Examples:
            ```
            # group instances intersected with each other
            fun = lambda a,b: a.bbox & b.bbox

            # group instances aligned horizontally
            fun = lambda a,b: a.horizontally_aligned_with(b)
            ```

            NOTE: it's equal to a GRAPH searching problem, build adjacent list, and then search graph 
            to find all connected components.
        '''
        # build adjacent list:
        # the i-th item is a set of indexes, which connected to the i-th instance.
        # NOTE: O(n^2) method, but it's acceptable (~0.2s) when n<1000 which is satisfied by page blocks
        num = len(self._instances)
        index_groups = [set() for i in range(num)] # type: list[set]        
        for i, instance in enumerate(self._instances):
            # connections of current instance to all instances after it
            for j in range(i+1, num):
                if fun(instance, self._instances[j]):
                    index_groups[i].add(j)
                    index_groups[j].add(i)

        # search graph
        # NOTE: generally a disconnected graph
        counted_indexes = set() # type: set[int]
        groups = []
        for i in range(num):
            if i in counted_indexes: continue
            # connected component starts...
            indexes = set(graph_BFS(index_groups, i))
            groups.append([self._instances[x] for x in indexes])
            counted_indexes = counted_indexes | indexes

        # final grouped instances
        groups = [self.__class__(group) for group in groups]

        return groups



class Collection(BaseCollection, IText):
    '''Collection of specific instances.'''
    def __init__(self, instances:list=[], parent=None):
        '''Init collection from a list of BBox instances.'''
        self._parent = parent # type: BBox
        super().__init__(instances)


    @property
    def parent(self): return self._parent   


    @property
    def bbox(self):
        '''bbox of combined collection.'''
        Box = BBox()
        for instance in self._instances:
            Box.union(instance)
        return Box.bbox


    @property
    def text_direction(self):
        '''Get text direction. All instances must have same text direction.''' 
        if self._instances and hasattr(self._instances[0], 'text_direction'):
            res = set(instance.text_direction for instance in self._instances)
            if len(res)==1:
                return list(res)[0]

        # normal direction by default
        return TextDirection.LEFT_RIGHT 


    def from_dicts(self, *args, **kwargs):
        '''Construct Collection from a list of dict.'''
        raise NotImplementedError


    def _update(self, bbox:BBox):
        '''Update parent of bbox, and the bbox of parent.'''
        if not self._parent is None: # Note: `if self._parent` does not work here
            self._parent.union(bbox)


    def append(self, bbox:BBox):
        '''Append an instance and update parent's bbox accordingly.'''
        if not bbox: return
        self._instances.append(bbox)
        self._update(bbox)


    def extend(self, bboxes:list):
        '''Append a list of instances.'''
        for bbox in bboxes:
            self.append(bbox)


    def reset(self, bboxes:list=[]):
        '''Reset instances list.'''
        self._instances = []
        self.extend(bboxes)
        return self


    def insert(self, nth:int, bbox:BBox):
        '''Insert a BBox and update parent's bbox accordingly.'''
        if not bbox: return
        self._instances.insert(nth, bbox)
        self._update(bbox)


    def sort_in_reading_order(self):
        '''Sort collection instances in reading order (considering text direction), e.g.
            for normal reading direction: from top to bottom, from left to right.
        '''
        if self.is_horizontal_text:
            self._instances.sort(key=lambda instance: (instance.bbox.y0, instance.bbox.x0, instance.bbox.x1))
        else:
            self._instances.sort(key=lambda instance: (instance.bbox.x0, instance.bbox.y1, instance.bbox.y0))
        return self


    def sort_in_line_order(self):
        '''Sort collection instances in a physical with text direction considered, e.g.
            for normal reading direction: from left to right.
        '''
        if self.is_horizontal_text:
            self._instances.sort(key=lambda instance: (instance.bbox.x0, instance.bbox.y0, instance.bbox.x1))
        else:
            self._instances.sort(key=lambda instance: (instance.bbox.y1, instance.bbox.x0, instance.bbox.y0))
        return self


    def store(self):
        '''Store attributes in json format.'''
        return [ instance.store() for instance in self._instances ]