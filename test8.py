from pymongo import MongoClient
from shapely.geometry import LineString
from shapely.geometry.polygon import LinearRing
from shapely.geometry import Polygon
from bson import json_util 
import numpy as np
import time
import pprint
import json 
import csv
import os
import shutil
import concurrent.futures
import subprocess

    
    
if __name__ == '__main__':
  start_time = time.time();
  print('-- main ---');
  
  #main_dir = '/data01/shared/tcga_analysis/seer_data/results';
  my_home='/home/bwang/shapely/';
  main_dir =os.path.join(my_home, 'results/'); 
  out_dir  =os.path.join(my_home, 'composite_results/');
  remote_folder="nfs001:/data/shared/tcga_analysis/seer_data/";  
  analysis_list_csv = os.path.join(my_home, 'analysis_list.csv');         
  if not os.path.isfile(analysis_list_csv):
    remote_file = os.path.join(remote_folder, 'analysis_list.csv');
    subprocess.call(['scp', remote_file,analysis_list_csv]); 
  #analysis_list_csv="/home/bwang/shapely/analysis_list.csv";
  
  prefixs_algorithm=[[0 for y in xrange(2)] for x in xrange(20)];    

  db_host="quip3.bmi.stonybrook.edu"
  db_port="27017"
  case_id="17035671"
  subject_id="17035671"
  execution_id="helen.wong_composite_input" 
  new_execution_id="helen.wong_composite_dataset";
  
  client = MongoClient('mongodb://'+db_host+':'+db_port+'/')
  #client = MongoClient('mongodb://quip3.bmi.stonybrook.edu:27017/')
  db = client.quip;
  objects = db.objects;
  metadata=db.metadata;    
  
  algorithms=[];
  prefixs=[];
  for algorithm in objects.distinct("algorithm",{"provenance.image.case_id":case_id,
                                             "provenance.image.subject_id":subject_id,
                                             "provenance.analysis.execution_id":execution_id}): 
    algorithms.append(algorithm);
    #print algorithm;
  #print algorithms;
  #print algorithms[0],algorithms[1];
  
  print '--- read master CSV file & load into list ---- ';
  index=0;
  with open(analysis_list_csv, 'r') as my_file:
    reader = csv.reader(my_file, delimiter=',')
    my_list = list(reader);
    for each_row in my_list:
      case_id_row=each_row[0];
      prefix=each_row[1];
      algorithm_row=each_row[2];      
      if (case_id_row == case_id and algorithm_row in algorithms):
        #print case_id,prefix,algorithm_row;
        prefixs.append(prefix); 
        prefixs_algorithm[index][0] = prefix;
        prefixs_algorithm[index][1] = algorithm_row;
        index+=1;
  print prefixs_algorithm;
  total_algorithms=index;
  print total_algorithms
  #exit();
  #print prefixs;
  #print algorithms;
  
  #copy all csv and json file from nfs001 node
  print '--- copy all csv and json file from nfs001 node ---- ';
  start_copy_time = time.time();
  for index1 in range (0,total_algorithms):
    prefix    = prefixs_algorithm[index1][0];  
    algorithm = prefixs_algorithm[index1][1];
    remote_root ='nfs001:/data/shared/tcga_analysis/seer_data/results/';
    remote_img_folder = os.path.join(remote_root, case_id);
    remote_folder = os.path.join(remote_img_folder, prefix);
    local_root  ='/home/bwang/shapely/results/';
    local_img_folder = os.path.join(local_root, case_id);
    local_folder = os.path.join(local_img_folder, prefix);
    if not os.path.exists(local_folder):
      print '%s folder do not exist, then reate it.';
      os.makedirs(local_folder);
    subprocess.call(['scp', remote_folder+'/*.json',local_folder]);
    subprocess.call(['scp', remote_folder+'/*features.csv',local_folder]);
  total_copy_time = time.time() - start_copy_time;  
  print "total time:"+str(total_copy_time/60.00)+ ' minutes.';
  exit();   
         
  
  
  print '----- get human markups by one user -----'; 
  polygon_algorithm=[[0 for y in xrange(2)] for x in xrange(200)]; 
  index=0;  
  for annotation in objects.find({"provenance.image.case_id":case_id,
              "provenance.image.subject_id":subject_id,
             "provenance.analysis.execution_id": execution_id
            },{"_id":0,"geometry.coordinates":1,"algorithm":1}):  
    polygon=annotation["geometry"]["coordinates"][0];
    algorithm=annotation["algorithm"];
    polygon_algorithm[index][0]=algorithm;
    polygon_algorithm[index][1]=polygon;  
    index+=1;
  print 'total annotation number is %d' % index; 
  total_annotation_count = index;
  #print polygon_algorithm[0][1];
  print 'this polygon point count is %d' % len(polygon_algorithm[0][1]); 
  
  print '-- find all annotations NOT within another annotation  -- ';
  polygon_algorithm_final=[[0 for y in xrange(3)] for x in xrange(200)]; 
  index3=0
  for index1 in range(0, total_annotation_count):
    algorithm = polygon_algorithm[index1][0]; 
    annotation = polygon_algorithm[index1][1]; 
    tmp_poly=[tuple(i) for i in annotation];
    annotation_polygon1 = Polygon(tmp_poly);
    annotation_polygon_1 = annotation_polygon1.buffer(0);
    polygonBound= annotation_polygon_1.bounds;
    array_size=len(annotation);
    print '-----------------------------------------------------------------';
    print "annotation index %d and annotation point size %d" % (index1, array_size) ;
    is_within=False;
    for index2 in range(0, total_annotation_count):
      annotation2 = polygon_algorithm[index2][1]; 
      tmp_poly2=[tuple(j) for j in annotation2];
      annotation_polygon2 = Polygon(tmp_poly2);
      annotation_polygon_2 = annotation_polygon2.buffer(0);
      #if not annotation_polygon_1.equals(annotation_polygon_2):  
      if index1 <> index2 and not annotation_polygon_1.equals(annotation_polygon_2):  
        if (annotation_polygon_1.within(annotation_polygon_2)):    
          is_within=True;
          polygonBound2= annotation_polygon_2.bounds;
          array_size2=len(annotation2); 
          print polygonBound;     
          print '-- find within polygon --';        
          print "annotation index %d and annotation point size %d" % (index2, array_size2) ;
          print polygonBound2;
          print '--------';
          break 
             
    if not is_within:
      print 'add annotation of index %d' % index1;
      polygon_algorithm_final[index3][0]=algorithm; 
      polygon_algorithm_final[index3][1]=annotation;
      polygon_algorithm_final[index3][2]=index1;
      index3+=1;
  print 'final annotation number is %d' % index3;  
  #print  polygon_algorithm_final[35][2];   
  final_total_annotation_count=index3;
  print final_total_annotation_count;
  #exit();
  
  
  print '------ get all tiles as polygon ------ ';
  title_polygon_algorithm_final=[[0 for y in xrange(3)] for x in xrange(10000)];
  print 'total_algorithms is %s' % total_algorithms;  
  for index1 in range (0,total_algorithms):
    prefix = prefixs_algorithm[index1][0];  
    algorithm = prefixs_algorithm[index1][1];
    img_folder = os.path.join(main_dir, case_id);
    #print img_folder;
    algorithm_folder = os.path.join(img_folder, prefix);  
    print '----------------------------------------------------';   
    print 'algorithm data files location %s' % algorithm_folder;
    #print os.listdir(algorithm_folder);
    if os.path.isdir(algorithm_folder) and len(os.listdir(algorithm_folder)) > 0:                            
      json_filename_list = [f for f in os.listdir(algorithm_folder) if f.endswith('.json')] ;
      print 'there are %d json files in this folder.' % len(json_filename_list);
      tmp_title_polygon=[];      
      for json_filename in json_filename_list:             
        with open(os.path.join(algorithm_folder, json_filename)) as f:
          data = json.load(f);
          analysis_id=data["analysis_id"];
          image_width=data["image_width"];
          image_height=data["image_height"];
          tile_minx=data["tile_minx"];
          tile_miny=data["tile_miny"];
          tile_width=data["tile_width"];
          tile_height=data["tile_height"];
          title_polygon=[[float(tile_minx)/float(image_width),float(tile_miny)/float(image_height)],[float(tile_minx+tile_width)/float(image_width),float(tile_miny)/float(image_height)],[float(tile_minx+tile_width)/float(image_width),float(tile_miny+tile_height)/float(image_height)],[float(tile_minx)/float(image_width),float(tile_miny+tile_height)/float(image_height)],[float(tile_minx)/float(image_width),float(tile_miny)/float(image_height)]];
          #print title_polygon;
          tmp_list=[[],[]];
          tmp_list[0]=json_filename;
          tmp_list[1]=title_polygon;
          tmp_title_polygon.append(tmp_list);
      print 'tmp title polygon length %d' % len(tmp_title_polygon);        
    title_polygon_algorithm_final[index1][0]=prefix;
    title_polygon_algorithm_final[index1][1]=algorithm;
    title_polygon_algorithm_final[index1][2]=tmp_title_polygon ;    
    print 'index1 is %d '% index1;
    #print  title_polygon_algorithm_final[index1][2]; 
    print  'there are %d titles in folder %s .' % (len(title_polygon_algorithm_final[index1][2]) ,algorithm_folder);      
  #exit();
  
  def process_one_tile(title_index,title_array,algorithm_folder_in,algorithm_folder_out):
    is_intersects=False;
    is_within=False;
    print  '--- current title_index is %d' % title_index;  
    #print  '--- current title algorithm  is %s' % algorithm1;    
    for index2 in range (0,final_total_annotation_count):
      algorithm2=polygon_algorithm_final[index2][0];         
      if (algorithm1 == algorithm2):
        json_filename=title_array[0];
        csv_filename=json_filename.replace('algmeta.json','features.csv');
        tmp_polygon=title_array[1];
        tmp_poly=[tuple(i) for i in tmp_polygon];
        title_polygon = Polygon(tmp_poly);
        title_polygon = title_polygon.buffer(0);
        annotation=polygon_algorithm_final[index2][1];        
        tmp_poly2=[tuple(j) for j in annotation];
        annotation_polygon = Polygon(tmp_poly2);
        annotation_polygon = annotation_polygon.buffer(0);
        if (title_polygon.within(annotation_polygon)): 
          is_within=True;
          break;
        elif (title_polygon.intersects(annotation_polygon)): 
          is_intersects=True;
          break;  
                              
    if (is_within or is_intersects):
      if is_intersects: 
        print '       title %d intersects with human markup %d' % (title_index,index2);
      if is_within:  
        print '       title %d is within with human markup %d' % (title_index,index2);        
      print '       json_filename is %s' % json_filename; 
      print '       csv_filename is %s' % csv_filename;        
      json_source_file = os.path.join(algorithm_folder_in, json_filename);
      csv_source_file = os.path.join(algorithm_folder_in, csv_filename);
      json_dest_file = os.path.join(algorithm_folder_out, json_filename);
      csv_dest_file = os.path.join(algorithm_folder_out, csv_filename);         
      if not os.path.isfile(json_dest_file):
        shutil.copy2(json_source_file,json_dest_file) ;
        #subprocess.call(['scp', json_source_file,json_dest_file]); 
      if not os.path.isfile(csv_dest_file):  
        shutil.copy2(csv_source_file,csv_dest_file) ; 
        #subprocess.call(['scp', csv_source_file,csv_dest_file]);
      #update analysis_id info in json file    
      with open(json_dest_file, 'r') as f:
       json_data = json.load(f)
       analysis_id = json_data['analysis_id'];
       image_width=json_data["image_width"];
       image_height=json_data["image_height"];
       json_data['analysis_id'] = new_execution_id;
       json_data['analysis_desc'] = analysis_id;
      with open(json_dest_file, 'w') as f2:
        f2.write(json.dumps(json_data));          
        #handle intersect of title and human markup  
    #else:
      #print 'this tile NOT intersect with any human markup.';
          
    #if is_intersects:   
      #print ' -- edit features.csv file as necessary -- '; 
      #my_tem_file ='tmp_file_'+ str(title_index)+'.csv';      
      #tmp_file = os.path.join(algorithm_folder_out, my_tem_file);
      #with open(csv_dest_file, 'rb') as csv_read, open(tmp_file, 'wb') as csv_write:
        #reader = csv.reader(csv_read);
        #headers = reader.next();          
        #write header to tmp file
        #csv_writer = csv.writer(csv_write);
        #csv_writer.writerow(headers);                      
        #column = {};
        #for h in headers:
          #column[h] = [];          
        #for row in reader:
          #for h, v in zip(headers, row):
            #column[h].append(v);              
          #current_polygon=column['Polygon'][-1] ;
          #new_polygon=[];      
          #tmp_str=str(current_polygon);            
          #tmp_str=tmp_str.replace('[','');
          #tmp_str=tmp_str.replace(']','');
          #split_str=tmp_str.split(':');
          #for i in range(0, len(split_str)-1, 2):
            #point=[float(split_str[i])/float(image_width),float(split_str[i+1])/float(image_height)];
            #new_polygon.append(point);              
          #tmp_poly=[tuple(i) for i in new_polygon];
          #computer_polygon = Polygon(tmp_poly);
          #computer_polygon = computer_polygon.buffer(0);
          #has_intersects=False;
          #for index2 in range (0,final_total_annotation_count):
            #annotation=polygon_algorithm_final[index2][1];        
            #tmp_poly2=[tuple(j) for j in annotation];
            #annotation_polygon = Polygon(tmp_poly2);
            #annotation_polygon = annotation_polygon.buffer(0);
            #if (computer_polygon.intersects(annotation_polygon)): 
              #has_intersects=True;
              #break;
          #write each row to the tmp csv file
          #if has_intersects:  
            #csv_writer.writerow(row) ;                           
      #shutil.move(tmp_file,csv_dest_file); 
      #print 'change tem file of %s  to file %s' % (tmp_file,csv_dest_file);  
          
          
  print"------------------------------------------------------";      
  print" -- find all title intersect with human markups -- ";  
  thread_list = [];
  total_algorithms=1;
  for index1 in range (0,total_algorithms):
    prefix=title_polygon_algorithm_final[index1][0];
    algorithm1=title_polygon_algorithm_final[index1][1];
    tmp_title_polygon_list=title_polygon_algorithm_final[index1][2];
    img_folder = os.path.join(main_dir, case_id);
    algorithm_folder = os.path.join(img_folder, prefix);
    out_folder = os.path.join(out_dir, case_id);
    out_algorithm_folder = os.path.join(out_folder, prefix);
    if not os.path.exists(out_algorithm_folder):
      os.makedirs(out_algorithm_folder);
    #print tmp_title_polygon;
    print " --------- deal with algorithm %s -------------- " % algorithm1; 
    title_index=0;
    #multiple thread  
    #with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
      #for tmp_title_polygon in tmp_title_polygon_list:
        #executor.submit(process_one_tile, title_index,tmp_title_polygon,algorithm_folder,out_algorithm_folder);
        #title_index+=1;
    # single thread    
    for tmp_title_polygon in tmp_title_polygon_list:  
      process_one_tile(title_index,tmp_title_polygon,algorithm_folder,out_algorithm_folder);
      title_index+=1;        
              
    #for tmp_title_polygon in tmp_title_polygon_list:  
      #start_time = time.time();        
      #t = ThreadPool.Thread(target=process_one_tile, args=(title_index,tmp_title_polygon,algorithm_folder,out_algorithm_folder))
      #t = threading.Thread(target=process_one_tile, args=(title_index,tmp_title_polygon,algorithm_folder,out_algorithm_folder))  
      #thread_list.append(t)
      #process_one_tile(title_index,tmp_title_polygon);                                                         
      #title_index+=1; 
      #elapsed_time = time.time() - start_time  
      #print "total time to handle tile %d is %s seconds." % (title_index ,str(elapsed_time));  
  
  # Starts threads
  #for thread in thread_list:
    #thread.start();

  # This blocks the calling thread until the thread whose join() method is called is terminated.
  # From http://docs.python.org/2/library/threading.html#thread-objects
  #for thread in thread_list:
    #thread.join();

  #Demonstrates that the main process waited for threads to complete
  print "Done"
  print '--- end of program ---';
  elapsed_time = time.time() - start_time  
  print "total time:"+str(elapsed_time/60.00)+ ' minutes.';
  exit(); 
    
  print"------------------------------------------------------";      
  print" -- find all title intersect with human markups -- ";  
  for index1 in range (0,total_algorithms):
    prefix=title_polygon_algorithm_final[index1][0];
    algorithm1=title_polygon_algorithm_final[index1][1];
    tmp_title_polygon_list=title_polygon_algorithm_final[index1][2];
    img_folder = os.path.join(main_dir, case_id);
    algorithm_folder = os.path.join(img_folder, prefix);
    out_folder = os.path.join(out_dir, case_id);
    out_algorithm_folder = os.path.join(out_folder, prefix);
    if not os.path.exists(out_algorithm_folder):
      os.makedirs(out_algorithm_folder);
    #print tmp_title_polygon;
    print " --------- deal with algorithm %s -------------- " % algorithm1; 
    title_index=0;    
    for tmp_title_polygon in tmp_title_polygon_list:  
      start_time = time.time();    
      process_one_tile(title_index,tmp_title_polygon);                                                         
      title_index+=1; 
      elapsed_time = time.time() - start_time  
      print "total time to handle tile %d is %s seconds." % (title_index ,str(elapsed_time));    
  print '--- end of program ---';
